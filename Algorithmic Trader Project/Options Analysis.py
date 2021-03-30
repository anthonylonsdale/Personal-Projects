"""
This program is the start of the Options variant of the Algo Trader, as such, for the time being it will perform
the regular options table export to excel, but we need to gut out all trading components and only focus on options
and options pricing
"""
import requests
import alpaca_trade_api as trade_api
import pandas as pd
import datetime as dt
import openpyxl
import os
import clr
import dateutil.relativedelta as rel
import subprocess


# uses our c# script as a dll in order to retrieve stock quotes and other information incredibly quickly
def stock_data_engine():
    clr.AddReference(r"C:\Users\fabio\source\repos\Webscraper Class Library\Webscraper Class Library\bin\Debug\Web"
                     r"scraper Class Library.dll")
    import CSharpwebscraper
    scraper = CSharpwebscraper.Webscraper()
    stock_info = scraper.Scraper(stock_tickers)
    print(stock_info)
    quote = {}
    for i in range(len(stock_info)):
        if (i % 6) == 0:
            quote['current price'] = float(stock_info[i].replace(",", ""))
        if (i % 6) == 1:
            quote['open price'] = float(stock_info[i].replace(",", ""))
        if (i % 6) == 2:
            quote['previous close'] = float(stock_info[i].replace(",", ""))
        if (i % 6) == 3:
            quote['indicator'] = str(stock_info[i])
        if (i % 6) == 4:
            delimiter1 = '('
            delimiter2 = ')'
            div = str(stock_info[i])
            dividend = div[div.find(delimiter1)+1: div.find(delimiter2)]
            if dividend == 'N/A':
                dividend = 0
            else:
                div_string = dividend.split("%")[0]
                dividend = float(div_string) / 100
            quote['dividend'] = dividend
        if (i % 6) == 5:
            stock = str(stock_info[i])
            quote['stock'] = stock
            quote['time'] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            quote_data[stock].append(quote)
            quote = {}
            df_quote = pd.DataFrame(quote_data[stock])
            df_quote.set_index('time', inplace=True)
            print(df_quote)


"""
this function is the main handler for the options data, specifically, it creates excel sheets for each stock that is
inputted, and creates two sheets per stock, one for the put options, and one for the call options
the formatting_excel function autofits each column automatically so the file is readable if you wish to look at the
options contracts for whatever reason
the options_calculations function uses custom-built c++ scripts to calculate the price of an options contract. It does
this through a modified Black-Scholes equation called a Binomial Tree. These options prices are then compared to the
actual options prices we have retrieved from Yahoo! Finance. 
Theoretically:
If, for example, the call options are overvalued, we can anticipate that traders will start selling off call options
and purchasing equivalent positions of stock. This creates an artificial short-term increase in the stock price that we 
can exploit (but I have not yet implemented it as I am still experimenting with it).
"""


def options():
    book = openpyxl.load_workbook('Options Data.xlsx')
    writer = pd.ExcelWriter('Options Data.xlsx', engine='openpyxl')
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    for stock in stock_tickers:
        link = 'https://finance.yahoo.com/quote/' + stock + '/options?p=' + stock + '&straddle=false'
        html = requests.get(link).content
        df_list = pd.read_html(html)
        call_table = df_list[0]
        call_table.set_index('Strike', inplace=True)
        print("CALL CONTRACTS FOR {}".format(stock))
        print(call_table)
        call_table.to_excel(writer, sheet_name=stock + ' Call Contracts')
        put_table = df_list[1]
        put_table.set_index('Strike', inplace=True)
        print("PUT CONTRACTS FOR {}".format(stock))
        print(put_table)
        put_table.to_excel(writer, sheet_name=stock + ' Put Contracts')
        writer.save()
    try:
        sheet = book['Sheet']
        book.remove(sheet)
        book.save('Options Data.xlsx')
    except KeyError:
        pass
    options_calculations()


# not yet fully implemented
def options_calculations():
    todays_date = dt.date.today()
    rel_date = rel.relativedelta(days=1, weekday=rel.FR)
    next_friday = todays_date + rel_date
    for stock in stock_tickers:
        options_seesaw[stock] = {'overvalued_call_options': 0, 'undervalued_call_options': 0,
                                 'overvalued_put_options': 0, 'undervalued_put_options': 0}
        df_calls = pd.read_excel("Options Data.xlsx", sheet_name=stock + ' Call Contracts')
        dividend = str(quote_data[stock][-1]['dividend'])
        spot = str(quote_data[stock][-1]['current price'])
        rate = '0.01'
        time_dt = next_friday - todays_date
        time_to_expiry = str(time_dt)
        iterations = '1000'
        print('CALLS')
        for i in range(len(df_calls.index)-1):
            """
            the subprocess returns nan for implied volatility of 0, just skip the options with imp. vol == 0
            also skip the options we dont care about, any open with open interest of less than 10 can have a manipulated
            price
            """
            vol_percentage = str(df_calls['Implied Volatility'][i])
            vol = vol_percentage.split("%")[0]
            volatility = float(vol.replace(",", "")) / 100
            if volatility == 0.00:
                continue
            if df_calls['Open Interest'][i] == '-' or int(df_calls['Open Interest'][i]) < 10:
                continue

            strike = str(df_calls['Strike'][i])
            sigma = str(volatility)

            output = subprocess.check_output(
                [r"C:\Users\fabio\OneDrive\Documents\C++ Experiments\C++ Options Pricing\projects"
                 r"\options_pricing\callpricing.exe",
                 spot, strike, rate, time_to_expiry, sigma, dividend, iterations])
            output_string = output.decode(encoding='utf-8', errors='strict')
            # print(output_string)
            option_price = float(output_string)

            print(strike, option_price)
            # if calculated option price is higher than the actual price, the actual option is undervalued
            if option_price > float(df_calls['Last Price'][i]):
                options_seesaw[stock]['undervalued_call_options'] += 1
            # if the opposite is true, the actual option is overvalued
            if option_price < float(df_calls['Last Price'][i]):
                options_seesaw[stock]['overvalued_call_options'] += 1

    #######################################################################################################
        print('--------------------------------------------------------------------------------------------')
        df_puts = pd.read_excel("Options Data.xlsx", sheet_name=stock + ' Put Contracts')
        print("PUTS")
        for i in range(len(df_puts.index)):
            vol_percentage = str(df_puts['Implied Volatility'][i])
            vol = vol_percentage.split("%")[0]
            volatility = float(vol.replace(",", "")) / 100
            if volatility == 0.00:
                continue
            if df_puts['Open Interest'][i] == '-' or int(df_puts['Open Interest'][i]) < 10:
                continue
            strike = str(df_puts['Strike'][i])
            sigma = str(volatility)

            output = subprocess.check_output(
                [r"C:\Users\fabio\OneDrive\Documents\C++ Experiments\C++ Options Pricing\projects"
                 r"\options_pricing\putpricing.exe",
                 spot, strike, rate, time_to_expiry, sigma, dividend, iterations])

            output_string = output.decode(encoding='utf-8', errors='strict')
            # print(output_string)
            option_price = float(output_string)
            print(strike, option_price)
            if option_price > float(df_puts['Last Price'][i]):
                options_seesaw[stock]['undervalued_put_options'] += 1
            if option_price < float(df_puts['Last Price'][i]):
                options_seesaw[stock]['overvalued_put_options'] += 1
    print(options_seesaw)


if __name__ == '__main__':
    # we want to make sure a new excel file is used each time the program opens to reduce issues of corrupted files
    cwd = os.getcwd() + r'\Options Data.xlsx'
    if os.path.isfile(r"{}".format(cwd)):
        os.remove("Options Data.xlsx")
    wb = openpyxl.Workbook()
    wb.save('Options Data.xlsx')
    # manual
    print("Input stock tickers separated by a space, the quotes and trades for each stock will be streamed")
    print("When you are done entering tickers, press Enter to show the quotes for each stock in order")
    stock_tickers = input('Enter Ticker(s): ').upper().split()
    #############################################################################################################
    key = "PK5S3WI3U5I3OBCZV82C"
    sec = "xfR7UlCNxngZbkriUvyIrk2rFNvR89IPw9epAK3d"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')
    account = api.get_account()
    account_balance = float(account.buying_power)
    print('Trading Account status:', account.status)
    date = dt.datetime.date(dt.datetime.now(dt.timezone.utc))
    # Get when the market opens or opened today
    print('The date is:', str(dt.date.today()), 'The time is', str(dt.datetime.now().time()), 'CST')
    clock = api.get_clock()
    market_close = str(clock.next_close)[:16:] + str(':00.000000')
    print("The market closes at {} o'clock EST today.".format(market_close[11:16:]),
          "Extended hours trading lasts for 4 hours before and after regular market hours.")
    #############################################################################################################
    try:
        quote_data = {}
        options_seesaw = {}
        for ticker in stock_tickers:
            quote_data[ticker] = []
            options_seesaw[ticker] = {}
        stock_data_engine()
        options()
    except Exception as e:
        print(e)
        raise Exception('An error has occurred...')
