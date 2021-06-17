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
        todays_date = dt.datetime.today().date()

        handle = ctypes.cdll.LoadLibrary(r"C:\Users\fabio\source\repos\CallPricingDll\CallPricingDll\x64\Rel"
                                         r"ease\CallPricingDll.dll")

        handle.CallPricing.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                                       ctypes.c_float, ctypes.c_float]
        handle.CallPricing.restype = ctypes.c_double

        handle.PutPricing.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                                      ctypes.c_float, ctypes.c_float]
        handle.PutPricing.restype = ctypes.c_double

        openpyxl.Workbook().save(f"{stock} Options Data {todays_date}.xlsx")
        book = openpyxl.load_workbook(f"{stock} Options Data {todays_date}.xlsx")
        writer = pd.ExcelWriter(f"{stock} Options Data {todays_date}.xlsx", engine='openpyxl')
        writer.book = book
        writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
        try:
            i = 0
            yfticker = yf.Ticker(stock)
            expiration_dates = yfticker.options
            dividend = self.initial_data[stock][0]
            spot = self.quote_data[stock][0]

            for expiry in expiration_dates:
                options_chain = yfticker.option_chain(expiry)
                call_table = options_chain.calls
                put_table = options_chain.puts
                call_table['option_value'] = 0.00
                put_table['option_value'] = 0.00

                self.option_value[stock].append({expiry: {'overvalued_call_options': 0, 'undervalued_call_options': 0,
                                                          'overvalued_put_options': 0, 'undervalued_put_options': 0}})
                exp = dt.datetime.strptime(expiry, '%Y-%m-%d')
                time_dt = exp - dt.datetime.today()
                time_to_expiry = time_dt.days + 1

                for index, row in call_table.iterrows():
                    sigma = row['impliedVolatility']
                    if sigma == 0.00:
                        continue
                    if row['openInterest'] < 10:
                        continue

                    strike = row['strike']
                    option_price = handle.CallPricing(spot, strike, self.rate, time_to_expiry, sigma, dividend)
                    call_table.at[index, 'option_value'] = option_price

                    if option_price > row['lastPrice']:
                        self.option_value[stock][i][expiry]['undervalued_call_options'] += 1
                    if option_price < row['lastPrice']:
                        self.option_value[stock][i][expiry]['overvalued_call_options'] += 1

                for index, row in put_table.iterrows():
                    sigma = row['impliedVolatility']
                    if sigma == 0.00:
                        continue
                    if row['openInterest'] < 10:
                        continue

                    strike = row['strike']
                    option_price = handle.PutPricing(spot, strike, self.rate, time_to_expiry, sigma, dividend)
                    put_table.at[index, 'option_value'] = option_price

                    if option_price > row['lastPrice']:
                        self.option_value[stock][i][expiry]['undervalued_put_options'] += 1
                    if option_price < row['lastPrice']:
                        self.option_value[stock][i][expiry]['overvalued_put_options'] += 1
                i += 1
                call_table.to_excel(writer, sheet_name=f'{stock} Calls {expiry}')
                put_table.to_excel(writer, sheet_name=f'{stock} Puts {expiry}')
        finally:
            book.save(f"{stock} Options Data {todays_date}.xlsx")
