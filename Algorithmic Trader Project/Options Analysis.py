"""
This program is the start of the Options variant of the Algo Trader, as such, for the time being it will perform
the regular options table export to excel, but we need to gut out all trading components and only focus on options
and options pricing
"""
import requests
import datetime as dt
import clr
import pandas as pd
import ctypes
from bs4 import BeautifulSoup
import yfinance as yf
import openpyxl
import concurrent.futures


def stock_data_engine():
    clr.AddReference(r"C:\Users\fabio\source\repos\Webscraper Class Library\Webscraper Class Library\bin\Debug\Web"
                     r"scraper Class Library.dll")
    import CSharpwebscraper
    scraper = CSharpwebscraper.Webscraper()
    stock_info = scraper.Initial(stock_tickers)
    quote_info = scraper.Scraper(stock_tickers)

    current_stock = None
    for index, item in enumerate(quote_info):
        if item in stock_tickers:
            current_stock = item
            continue
        if index % 6 == 1:
            item = item.replace(',', '')
            item = float(item)
        quote_data[current_stock].append(item)

    current_stock = None
    for index, item in enumerate(stock_info):
        if item in stock_tickers:
            current_stock = item
            continue
        if index % 10 == 1:
            delimiter1 = '('
            delimiter2 = ')'
            div = str(item)
            dividend = div[div.find(delimiter1) + 1: div.find(delimiter2)]
            if dividend == 'N/A':
                item = 0.00
            else:
                div_string = dividend.split("%")[0]
                dividend = float(div_string) / 100
                item = round(dividend, 4)
        initial_data[current_stock].append(item)
        if index % 10 == 9:
            initial_data[current_stock].append(dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print(initial_data)
    print(quote_data)


def options(stock):
    todays_date = dt.datetime.today().date()
    iterations = 1000

    handle = ctypes.cdll.LoadLibrary(r"C:\Users\fabio\source\repos\CallPricingDll\CallPricingDll\x64\Rel"
                                     r"ease\CallPricingDll.dll")

    handle.CallPricing.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double,
                                   ctypes.c_double, ctypes.c_double, ctypes.c_int]
    handle.CallPricing.restype = ctypes.c_double

    handle.PutPricing.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double,
                                  ctypes.c_double, ctypes.c_double, ctypes.c_int]
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

        dividend = initial_data[stock][0]
        spot = quote_data[stock][0]

        for expiry in expiration_dates:
            options_chain = yfticker.option_chain(expiry)
            call_table = options_chain.calls
            put_table = options_chain.puts
            call_table.to_excel(writer, sheet_name=f'{stock} Calls {expiry}')
            put_table.to_excel(writer, sheet_name=f'{stock} Puts {expiry}')

            # 2 is strike, 3 is last price, 9 is open interest and 10 is implied volatility
            call_vals = call_table[call_table.columns[[2, 3, 9, 10]]].to_numpy()
            put_vals = put_table[put_table.columns[[2, 3, 9, 10]]].to_numpy()

            option_value[stock].append({expiry: {'overvalued_call_options': 0, 'undervalued_call_options': 0,
                                                 'overvalued_put_options': 0, 'undervalued_put_options': 0}})
            exp = dt.datetime.strptime(expiry, '%Y-%m-%d')
            time_dt = exp - dt.datetime.today()
            time_to_expiry = time_dt.days

            for index, row in enumerate(call_vals):
                sigma = row[3]
                if sigma == 0.00:
                    continue
                if row[2] < 10:
                    continue

                strike = row[0]
                option_price = handle.CallPricing(spot, strike, rate, time_to_expiry, sigma, dividend, iterations)
                if option_price > row[1]:
                    option_value[stock][i][expiry]['undervalued_call_options'] += 1
                if option_price < row[1]:
                    option_value[stock][i][expiry]['overvalued_call_options'] += 1

            for index, row in enumerate(put_vals):
                sigma = row[3]
                if sigma == 0.00:
                    continue
                if row[2] < 10:
                    continue

                strike = row[0]
                option_price = handle.PutPricing(spot, strike, rate, time_to_expiry, sigma, dividend, iterations)
                if option_price > row[1]:
                    option_value[stock][i][expiry]['undervalued_put_options'] += 1
                if option_price < row[1]:
                    option_value[stock][i][expiry]['overvalued_put_options'] += 1
            i += 1
    finally:
        book.save(f"{stock} Options Data {todays_date}.xlsx")


def risk_free_rate():
    r = requests.get('https://www.marketwatch.com/investing/bond/tmubmusd01m?countrycode=bx')
    soup = BeautifulSoup(r.text, 'lxml')
    bond_list = [entry.text for entry in
                 soup.find_all('bg-quote', {'channel': '/zigman2/quotes/211347041/realtime'})]
    bond_rate = float(bond_list[1])
    print("1 month risk-free-rate", str(bond_rate) + str('%'))
    return bond_rate


if __name__ == '__main__':
    # we want to make sure a new excel file is used each time the program opens to reduce issues of corrupted files
    date = dt.datetime.date(dt.datetime.now(dt.timezone.utc))
    print('The date is:', str(dt.date.today()), 'The time is', str(dt.datetime.now().time()), 'CST')
    # manual
    print("Input stock tickers separated by a space, the options chain for each stock will be gathered")
    print("When you are done entering tickers, press Enter to show the options contracts for each stock in order")
    stock_tickers = input('Enter Ticker(s): ').upper().split()
    #############################################################################################################
    initial_data = {}
    quote_data = {}
    option_value = {}
    for ticker in stock_tickers:
        initial_data[ticker] = []
        quote_data[ticker] = []
        option_value[ticker] = []
    rate = risk_free_rate()
    stock_data_engine()
    
    # this line increase performance dramatically
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(stock_tickers)) as executor:
        for stock in stock_tickers:
            future = executor.submit(options, stock)
    print(option_value)
