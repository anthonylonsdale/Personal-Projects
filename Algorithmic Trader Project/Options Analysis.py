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
import subprocess
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


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
            dividend = div[div.find(delimiter1) + 1: div.find(delimiter2)]
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


def options():
    expiration_dates = []
    expiration_date_timestamps = []
    driver = webdriver.Chrome(ChromeDriverManager().install())
    book = openpyxl.load_workbook('Options Data.xlsx')
    writer = pd.ExcelWriter('Options Data.xlsx', engine='openpyxl')
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    for stock in stock_tickers:
        link = 'https://finance.yahoo.com/quote/' + stock + '/options?p=' + stock + '&straddle=false'
        driver.get(link)
        html = driver.execute_script('return document.body.innerHTML;')
        soup = BeautifulSoup(html, 'lxml')
        expiration_dates = [entry.text for entry in soup.find_all(lambda tag: tag.name == 'option' and
                                                                  tag.get('value'))]
        i = 0
        for a in soup.findChildren("option"):
            expo = expiration_dates[i]
            print(expo)
            expiration_date_timestamps.append(a['value'])
            link = "https://finance.yahoo.com/quote/" + stock + '/options?date=' + str(a['value']) + str('&p=') + stock
            html = requests.get(link).content
            df_list = pd.read_html(html)
            call_table = df_list[0]
            call_table.set_index('Strike', inplace=True)
            print("CALL CONTRACTS FOR {} EXPIRING {}".format(stock, expo))
            print(call_table)
            call_table.to_excel(writer, sheet_name=stock + ' Calls ({})'.format(expo))
            put_table = df_list[1]
            put_table.set_index('Strike', inplace=True)
            print("PUT CONTRACTS FOR {} EXPIRING {}".format(stock, expo))
            print(put_table)
            put_table.to_excel(writer, sheet_name=stock + ' Puts ({})'.format(expo))
            writer.save()
            i += 1
    try:
        sheet = book['Sheet']
        book.remove(sheet)
        book.save('Options Data.xlsx')
    except KeyError:
        pass
    driver.quit()
    return expiration_dates, expiration_date_timestamps


def options_calculations(expiration_dates, expiration_date_integers):
    todays_date = dt.date.today()
    riskfreerate = str(rate)
    iterations = str('1000')
    for stock in stock_tickers:
        i = 0
        for expiration in expiration_dates:
            option_value[stock].append({expiration: {'overvalued_call_options': 0, 'undervalued_call_options': 0,
                                                     'overvalued_put_options': 0, 'undervalued_put_options': 0}})

            call_sheet_name = str(stock) + str(' Calls ({})').format(expiration)
            df_calls = pd.read_excel("Options Data.xlsx", sheet_name=call_sheet_name)
            dividend = str(quote_data[stock][-1]['dividend'])
            spot = str(quote_data[stock][-1]['current price'])

            timestamp = int(expiration_date_integers[i])
            expo_date = dt.datetime.utcfromtimestamp(timestamp).date()
            time_dt = expo_date - todays_date
            time_to_expiry = str(time_dt.days)
            print('CALLS')
            for j in range(len(df_calls.index) - 1):
                """ the subprocess returns nan for implied volatility of 0, just skip the options with imp. vol == 0
                also skip the options we dont care about, any open with open interest of less than 10 can have a 
                manipulated price """
                vol_percentage = str(df_calls['Implied Volatility'][j])
                vol = vol_percentage.split("%")[0]
                volatility = float(vol.replace(",", "")) / 100
                if volatility == 0.00:
                    continue
                if df_calls['Open Interest'][j] == '-' or int(df_calls['Open Interest'][j]) < 10:
                    continue

                strike = str(df_calls['Strike'][j])
                sigma = str(volatility)

                output = subprocess.check_output(
                    [r"C:\Users\fabio\OneDrive\Documents\C++ Experiments\C++ Options Pricing\projects\options_pricing"
                     r"\callpricing.exe", spot, strike, riskfreerate, time_to_expiry, sigma, dividend, iterations])

                output_string = output.decode(encoding='utf-8', errors='strict')
                option_price = float(output_string)

                print(strike, option_price)
                # if calculated option price is higher than the actual price, the actual option is undervalued
                if option_price > float(df_calls['Last Price'][j]):
                    option_value[stock][i][expiration]['undervalued_call_options'] += 1
                # if the opposite is true, the actual option is overvalued.
                if option_price < float(df_calls['Last Price'][j]):
                    option_value[stock][i][expiration]['overvalued_call_options'] += 1

            #######################################################################################################
            print('--------------------------------------------------------------------------------------------')
            put_sheet_name = str(stock) + str(' Puts ({})').format(expiration)
            df_puts = pd.read_excel("Options Data.xlsx", sheet_name=put_sheet_name)
            print("PUTS")
            for k in range(len(df_puts.index)):
                vol_percentage = str(df_puts['Implied Volatility'][k])
                vol = vol_percentage.split("%")[0]
                volatility = float(vol.replace(",", "")) / 100
                if volatility == 0.00:
                    continue
                if df_puts['Open Interest'][k] == '-' or int(df_puts['Open Interest'][k]) < 10:
                    continue
                strike = str(df_puts['Strike'][k])
                sigma = str(volatility)

                output = subprocess.check_output(
                    [r"C:\Users\fabio\OneDrive\Documents\C++ Experiments\C++ Options Pricing\projects\options_pric"
                     r"ing\putpricing.exe", spot, strike, riskfreerate, time_to_expiry, sigma, dividend, iterations])

                output_string = output.decode(encoding='utf-8', errors='strict')

                option_price = float(output_string)
                print(strike, option_price)

                if option_price > float(df_puts['Last Price'][k]):
                    option_value[stock][i][expiration]['undervalued_put_options'] += 1
                if option_price < float(df_puts['Last Price'][k]):
                    option_value[stock][i][expiration]['overvalued_put_options'] += 1
            i += 1
    print(option_value)


def risk_free_rate():
    r = requests.get('https://www.marketwatch.com/investing/bond/tmubmusd01m?countrycode=bx')
    soup = BeautifulSoup(r.text, 'lxml')
    bond_list = [entry.text for entry in
                 soup.find_all('span', {'class': 'value'})]
    bond_rate = float(bond_list[-1])
    print("1 month risk-free-rate", str(bond_rate) + str('%'))
    return bond_rate


if __name__ == '__main__':
    # we want to make sure a new excel file is used each time the program opens to reduce issues of corrupted files
    cwd = os.getcwd() + r'\Options Data.xlsx'
    if os.path.isfile(r"{}".format(cwd)):
        os.remove("Options Data.xlsx")
    wb = openpyxl.Workbook()
    wb.save('Options Data.xlsx')

    date = dt.datetime.date(dt.datetime.now(dt.timezone.utc))
    print('The date is:', str(dt.date.today()), 'The time is', str(dt.datetime.now().time()), 'CST')
    # manual
    print("Input stock tickers separated by a space, the options chain for each stock will be gathered")
    print("When you are done entering tickers, press Enter to show the options contracts for each stock in order")
    stock_tickers = input('Enter Ticker(s): ').upper().split()
    #############################################################################################################
    quote_data = {}
    option_value = {}
    for ticker in stock_tickers:
        quote_data[ticker] = []
        option_value[ticker] = []
    rate = risk_free_rate()
    stock_data_engine()
    options_expirations, options_expirations_integers = options()
    options_calculations(options_expirations, options_expirations_integers)
