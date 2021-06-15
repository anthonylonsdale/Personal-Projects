"""
This program is the start of the Options variant of the Algo Trader, as such, for the time being it will perform
the regular options table export to excel, but we need to gut out all trading components and only focus on options
and options pricing
"""
import requests
import pandas as pd
import datetime as dt
import openpyxl
import os
import clr
import ctypes
from bs4 import BeautifulSoup
import yfinance as yf


def stock_data_engine():
    clr.AddReference(r"C:\Users\fabio\source\repos\Webscraper Class Library\Webscraper Class Library\bin\Debug\Web"
                     r"scraper Class Library.dll")
    import CSharpwebscraper
    scraper = CSharpwebscraper.Webscraper()
    stock_info = scraper.Initial(stock_tickers)
    quote_info = scraper.Scraper(stock_tickers)
    print(stock_info)
    print(quote_info)

    current_stock = None
    for index, item in enumerate(quote_info):
        if item in stock_tickers:
            current_stock = item
            continue
        if (index % 6 == 1):
            item = item.replace(',', '')
            item = float(item)
        quote_data[current_stock].append(item)

    current_stock = None
    for index, item in enumerate(stock_info):
        if item in stock_tickers:
            current_stock = item
            continue
        if (index % 10) == 1:
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
        if (index % 10) == 9:
            initial_data[current_stock].append(dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print(initial_data)
    print(quote_data)


def options():
    book = openpyxl.load_workbook('Options Data.xlsx')
    writer = pd.ExcelWriter('Options Data.xlsx', engine='openpyxl')
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    for stock in stock_tickers:
        ticker = yf.Ticker(stock)
        for exp in ticker.options:
            options = ticker.option_chain(exp)
            call_table = options.calls
            call_table.set_index('strike', inplace=True)
            call_table.to_excel(writer, sheet_name=stock + ' Calls ({})'.format(exp))
            put_table = options.puts
            put_table.set_index('strike', inplace=True)
            put_table.to_excel(writer, sheet_name=stock + ' Puts ({})'.format(exp))
            writer.save()
    try:
        sheet = book['Sheet']
        book.remove(sheet)
        book.save('Options Data.xlsx')
    except KeyError:
        pass


def options_calculations():
    todays_date = dt.datetime.today()
    iterations = 1000

    handle = ctypes.cdll.LoadLibrary(r"C:\Users\fabio\source\repos\CallPricingDll\CallPricingDll\x64\Rel"
                                     r"ease\CallPricingDll.dll")
    handle.CallPricing.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double,
                                   ctypes.c_double, ctypes.c_double, ctypes.c_int]
    handle.CallPricing.restype = ctypes.c_double

    handle2 = ctypes.cdll.LoadLibrary(r"C:\Users\fabio\source\repos\PutPricingDll\x64\Release\PutPricing.dll")
    handle2.PutPricing.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double,
                                   ctypes.c_double, ctypes.c_double, ctypes.c_int]
    handle2.PutPricing.restype = ctypes.c_double

    for stock in stock_tickers:
        i = 0
        ticker = yf.Ticker(stock)
        expiration_dates = ticker.options

        for expiry in expiration_dates:
            option_value[stock].append({expiry: {'overvalued_call_options': 0, 'undervalued_call_options': 0,
                                                 'overvalued_put_options': 0, 'undervalued_put_options': 0}})
            call_sheet_name = str(stock) + str(' Calls ({})').format(expiry)
            try:
                df_calls = pd.read_excel("Options Data.xlsx", sheet_name=call_sheet_name)
            except ValueError:
                continue
            dividend = initial_data[stock][0]
            spot = quote_data[stock][0]
            expiry = dt.datetime.strptime(expiry, '%Y-%m-%d')
            time_dt = expiry - todays_date
            time_to_expiry = time_dt.days
            for j in range(len(df_calls.index) - 1):
                """ the subprocess returns nan for implied volatility of 0, just skip the options with imp. vol == 0
                also skip the options we dont care about, any open with open interest of less than 10 can have a 
                manipulated price """
                vol_percentage = str(df_calls['impliedVolatility'][j])
                vol = vol_percentage.split("%")[0]
                volatility = float(vol.replace(",", "")) / 100
                if volatility == 0.00:
                    continue
                try:
                    if int(df_calls['openInterest'][j]) < 10:
                        continue
                except ValueError:
                    continue

                strike = df_calls['strike'][j]
                sigma = volatility

                option_price = handle.CallPricing(spot, strike, rate, time_to_expiry, sigma, dividend, iterations)
                # if calculated option price is higher than the actual price, the actual option is undervalued
                try:
                    if option_price > float(df_calls['lastPrice'][j]):
                        option_value[stock][i][expiry]['undervalued_call_options'] += 1
                    # if the opposite is true, the actual option is overvalued.
                    if option_price < float(df_calls['lastPrice'][j]):
                        option_value[stock][i][expiry]['overvalued_call_options'] += 1
                except KeyError:
                    pass
            #######################################################################################################
            put_sheet_name = str(stock) + str(' Puts ({})').format(expiry)
            try:
                df_puts = pd.read_excel("Options Data.xlsx", sheet_name=put_sheet_name)
            except ValueError:
                continue
            for k in range(len(df_puts.index)):
                vol_percentage = str(df_puts['impliedVolatility'][k])
                vol = vol_percentage.split("%")[0]
                volatility = float(vol.replace(",", "")) / 100
                if volatility == 0.00:
                    continue
                try:
                    if int(df_puts['openInterest'][k]) < 10:
                        continue
                except ValueError:
                    continue

                strike = df_puts['strike'][k]
                sigma = volatility

                option_price = handle2.PutPricing(spot, strike, rate, time_to_expiry, sigma, dividend, iterations)
                try:
                    if option_price > float(df_puts['lastPrice'][k]):
                        option_value[stock][i][expiry]['undervalued_put_options'] += 1
                    if option_price < float(df_puts['lastPrice'][k]):
                        option_value[stock][i][expiry]['overvalued_put_options'] += 1
                except KeyError:
                    pass
            i += 1
    print(option_value)


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
    options_cwd = os.getcwd() + r'\Options Data.xlsx'
    if os.path.isfile(r"{}".format(options_cwd)):
        os.remove(options_cwd)
    wb = openpyxl.Workbook()
    wb.save('Options Data.xlsx')

    date = dt.datetime.date(dt.datetime.now(dt.timezone.utc))
    print('The date is:', str(dt.date.today()), 'The time is', str(dt.datetime.now().time()), 'CST')
    # manual
    print("Input stock tickers separated by a space, the options chain for each stock will be gathered")
    print("When you are done entering tickers, press Enter to show the options contracts for each stock in order")
    stock_tickers = input('Enter Ticker(s): ').upper().split()
    #############################################################################################################
    start = dt.datetime.now()
    initial_data = {}
    quote_data = {}
    option_value = {}
    for ticker in stock_tickers:
        initial_data[ticker] = []
        quote_data[ticker] = []
        option_value[ticker] = []
    rate = risk_free_rate()
    stock_data_engine()
    options()
    options_calculations()
    print(dt.datetime.now() - start)
