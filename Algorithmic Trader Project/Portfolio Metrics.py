"""
THIS PROGRAM IS MEANT TO BE RUN AT THE END OF A TRADING DAY
DOESNT REALLY MATTER HOW LONG IT TAKES, SPEED ISN'T IMPORTANT
"""
import alpaca_trade_api as trade_api
from pandas import DataFrame
import datetime as dt
import pandas as pd
import openpyxl
import win32com.client as win32
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


def orders_to_excel(recent_orders, metrics):
    book = openpyxl.load_workbook('Portfolio Data.xlsx')
    writer = pd.ExcelWriter('Portfolio Data.xlsx', engine='openpyxl')
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    recent_orders.to_excel(writer, sheet_name='Orders')
    metrics.to_excel(writer, sheet_name='Portfolio Metrics')
    try:
        sheet = book['Sheet']
        book.remove(sheet)
        book.save('Portfolio Data.xlsx')
    except KeyError:
        pass
    writer.save()


def formatting_excel():
    excel = win32.gencache.EnsureDispatch('Excel.Application')
    wb = excel.Workbooks.Open(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Portfolio Data.xlsx")
    ws = wb.Worksheets('Orders')
    ws.Columns.AutoFit()
    ws2 = wb.Worksheets('Portfolio Metrics')
    ws2.Columns.AutoFit()
    wb.Save()
    excel.Application.Quit()


def webscraping(stock_tickers_involved):
    try:
        for stock in stock_tickers_involved:
            quote = {}
            stockurl = 'https://finance.yahoo.com/quote/' + stock + '?p=' + stock
            driver.get(stockurl)
            html = driver.execute_script('return document.body.innerHTML;')
            soup = BeautifulSoup(html, 'lxml')
            beta = [entry.text for entry in soup.find_all('span', {'data-reactid': '144'})]
            quote['stock'] = stock
            quote['beta'] = beta[0]
            quote_data[stock] = quote
        # spy
        url = 'https://finance.yahoo.com/quote/SPY?p=SPY'
        driver.get(url)
        html = driver.execute_script('return document.body.innerHTML;')
        soup = BeautifulSoup(html, 'lxml')
        beta = [entry.text for entry in soup.find_all('span', {'data-reactid': '51'})]
        delimiter1 = '('
        delimiter2 = ')'
        returnformatted = str(beta[0])
        rt = returnformatted[returnformatted.find(delimiter1) + 1: returnformatted.find(delimiter2)]
        return_string = rt.split("%")[0]
        spyreturn = float(return_string) / 100
        return spyreturn
    except Exception as e:
        print(e)
    finally:
        driver.quit()


if __name__ == '__main__':
    if not os.path.isfile(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Portfolio Data.xlsx"):
        wb = openpyxl.Workbook()
        wb.save('Portfolio Data.xlsx')

    key = "PKCPC6RJ84BG84W3PB60"
    sec = "U1r9Z2QknL9FwAaTztfLl5g1DTxpa5m97qyWCGZ7"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')
    #############################################################################
    account = api.get_account()
    todayspandl = float(account.equity) - float(account.last_equity)
    print("Todays profit/loss: $" + "{:0.2f}".format(todayspandl))
    #############################################################################
    timeperiod = 2
    tdys_date = dt.datetime.today() - dt.timedelta(days=timeperiod-1)
    todays_date = tdys_date.strftime('%Y-%m-%d')
    ystrdy = dt.datetime.today() - dt.timedelta(days=timeperiod)
    yesterday = ystrdy.strftime('%Y-%m-%d')
    portfolio = api.get_portfolio_history(date_start=yesterday, date_end=todays_date, timeframe="1Min")
    #############################################################################
    order_list = api.list_orders(status='closed', limit=200)
    df_orders = DataFrame([order._raw for order in order_list])
    print(df_orders)
    df_orders.drop(df_orders.columns[[1, 5, 6, 7, 8, 9, 10, 11]], axis=1, inplace=True)
    print(df_orders)
    #############################################################################
    stock_tickers_involved = df_orders['symbol'].tolist()
    stock_tickers_involved = list(set(stock_tickers_involved))
    print(stock_tickers_involved)
    #############################################################################
    oneyrriskfreerate = 0.11
    #############################################################################
    pd.options.display.float_format = '{:.0f}'.format
    driver = webdriver.Chrome(ChromeDriverManager().install())
    quote_data = {}
    for stock in stock_tickers_involved:
        quote_data[stock] = []

    #########################################################################################
    quote_data = {'MSFT': {'stock': 'MSFT', 'beta': '0.83'}, 'AMD': {'stock': 'AMD', 'beta': '2.28'}, 'AAPL': {'stock': 'AAPL', 'beta': '1.28'}, 'AMZN': {'stock': 'AMZN', 'beta': '1.20'}}
    spyreturn = 0.0057
    # spyreturn = webscraping(stock_tickers_involved)
    # spyreturn = '{:.4f}'.format(spyreturn)
    print(quote_data)
    #############################################################################
    account = api.get_account()
    print(spyreturn)
    for stock in stock_tickers_involved:
        # print(quote_data[stock])
        # print(quote_data[stock]['beta'])
        beta = float(quote_data[stock]['beta'])
        buying_power = float(account.buying_power) / 4
        portfolioreturnpct = (todayspandl / buying_power) * 100
        alphaMetric = (todayspandl - oneyrriskfreerate) - (beta * (spyreturn - oneyrriskfreerate))
        print(alphaMetric)


    data = [
        ['', 'All Trades', 'Long Trades', 'Short Trades'],
        ['Total Net Profit:', todayspandl, '123', '123'],
        ['Gross Profit:', '', '', ''],
        ['Gross Loss:', '', '', ''],
        ['Profit Factor:', '', '', ''],
        ['', '', '', ''],
        ['Total Number of Trades:', '', '', ''],
        ['Percent Profitable:', '', '', ''],
        ['Winning Trades:', '', '', ''],
        ['Losing Trades:', '', '', ''],
        ['Even Trades', '', '', '']
            ]
    portfolio_metrics = DataFrame(data, columns=['', 'All Trades', 'Long Trades', 'Short Trades'])

    orders_to_excel(df_orders, portfolio_metrics)
    formatting_excel()
