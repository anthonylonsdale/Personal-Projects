import datetime as dt
import pandas as pd
import ctypes
import yfinance as yf
import openpyxl
import concurrent.futures


class Options:
    def __init__(self, stock_tickers=None, initial_data=None, quote_data=None, rate=None):
        self.stock_tickers = stock_tickers
        self.initial_data = initial_data
        self.quote_data = quote_data
        self.rate = rate
        self.option_value = {}
        for ticker in stock_tickers:
            self.option_value[ticker] = []

    def thread_marshaller(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.stock_tickers)) as executor:
            for stock in self.stock_tickers:
                executor.submit(self.options, stock)

        return self.option_value

    def options(self, stock):
        today = dt.date.today()
        url = f"../ALGO/Daily Stock Analysis/Options/{stock} Options Data {today}.xlsx"

        handle = ctypes.cdll.LoadLibrary(r"C:\Users\fabio\source\repos\CallPricingDll\CallPricingDll\x64\Rel"
                                         r"ease\CallPricingDll.dll")

        handle.CallPricing.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                                       ctypes.c_float]
        handle.CallPricing.restype = ctypes.c_double
        handle.PutPricing.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double,
                                      ctypes.c_double]
        handle.PutPricing.restype = ctypes.c_double

        wb = openpyxl.Workbook()
        wb.save(url)
        book = openpyxl.load_workbook(url)
        writer = pd.ExcelWriter(url, engine='openpyxl')
        writer.book = book
        writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
        try:
            i = 0
            yfticker = yf.Ticker(stock)
            expiration_dates = yfticker.options
            dividend = self.initial_data[stock][0]
            spot = self.quote_data[stock][0]

            for expiry in expiration_dates:
                exp = dt.datetime.strptime(expiry, '%Y-%m-%d').date()
                days_expiration = exp - today
                time_to_expiry = int(days_expiration.days)

                bond_yield = float(self.rate[0])
                if 30 <= time_to_expiry <= 60:
                    bond_yield = float(self.rate[1])
                elif 60 < time_to_expiry <= 91:
                    bond_yield = float(self.rate[2])
                elif 91 < time_to_expiry <= 182:
                    bond_yield = float(self.rate[3])
                elif time_to_expiry > 182:
                    continue

                options_chain = yfticker.option_chain(expiry)
                call_table = options_chain.calls
                put_table = options_chain.puts
                call_table['option_value'] = 0.00
                put_table['option_value'] = 0.00

                self.option_value[stock].append({expiry: {'overvalued_call_options': 0, 'undervalued_call_options': 0,
                                                          'overvalued_put_options': 0, 'undervalued_put_options': 0}})
                # calls_well_priced = 0
                # total_calls = 0
                # puts_well_priced = 0
                # total_puts = 0

                bond_yield -= dividend  # dividend should be factored in
                bond_yield -= 0.02  # nominal inflation rate

                for index, row in call_table.iterrows():
                    sigma = row['impliedVolatility']
                    if sigma < 0.0001 or row['bid'] < 0.05 or row['volume'] < 10 or row['openInterest'] < 10:
                        continue

                    strike = row['strike']
                    option_price = handle.CallPricing(spot, strike, bond_yield, time_to_expiry, sigma)

                    call_table.at[index, 'option_value'] = option_price
                    spread = (row['bid'] + row['ask']) / 2
                    call_table.at[index, 'lastPrice'] = spread

                    # error = ((option_price - spread) / spread)
                    # if -0.05 < error < 0.05:
                    #     calls_well_priced += 1
                    # total_calls += 1

                    if option_price > spread:
                        self.option_value[stock][i][expiry]['undervalued_call_options'] += 1
                    if option_price < spread:
                        self.option_value[stock][i][expiry]['overvalued_call_options'] += 1

                for index, row in put_table.iterrows():
                    sigma = row['impliedVolatility']
                    if sigma == 0.00 or row['bid'] < 0.05 or row['volume'] < 10 or row['openInterest'] < 10:
                        continue
                    strike = row['strike']

                    option_price = handle.PutPricing(spot, strike, bond_yield, time_to_expiry, sigma)

                    put_table.at[index, 'option_value'] = float(option_price)
                    spread = (row['bid'] + row['ask']) / 2
                    put_table.at[index, 'lastPrice'] = spread

                    # error = ((option_price - spread) / spread)
                    # if -0.05 < error < 0.05:
                    #     puts_well_priced += 1
                    # total_puts += 1

                    if option_price > spread:
                        self.option_value[stock][i][expiry]['undervalued_put_options'] += 1
                    if option_price < spread:
                        self.option_value[stock][i][expiry]['overvalued_put_options'] += 1

                # pct_well_priced = (calls_well_priced / total_calls) * 100
                # pct_well_priced_2 = (puts_well_priced / total_puts) * 100
                # print(f"{round(pct_well_priced, 2)}% of calls well priced (within 5% of the bid/ask spread) "
                #       f"for {stock} options expiring {expiry}")
                # print(f"{round(pct_well_priced_2, 2)}% of puts well priced (within 5% of the bid/ask spread) "
                #       f"for {stock} options expiring {expiry}")
                i += 1
                call_table.to_excel(writer, sheet_name=f'{stock} Calls {expiry}')
                put_table.to_excel(writer, sheet_name=f'{stock} Puts {expiry}')
        except Exception as e:
            print(e)
        finally:
            try:
                sheet = book['Sheet']
                book.remove(sheet)
            except KeyError:
                pass
            book.save(url)
