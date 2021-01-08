from win10toast import ToastNotifier
from requests import get
import websocket
from json import loads
import threading as th
import alpaca_trade_api as trade_api
from pandas import DataFrame
import time
import datetime as dt
from clr import AddReference
import openpyxl

if __name__ == '__main__':
    key = "PKCPC6RJ84BG84W3PB60"
    sec = "U1r9Z2QknL9FwAaTztfLl5g1DTxpa5m97qyWCGZ7"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')

    account = api.get_account()
    todayspandl = float(account.equity) - float(account.last_equity)
    print("Todays profit/loss: $" + str(todayspandl))

    tdys_date = dt.datetime.today()
    todays_date = tdys_date.strftime('%Y-%m-%d')
    ystrdy = dt.datetime.today() - dt.timedelta(days=1)
    yesterday = ystrdy.strftime('%Y-%m-%d')
    portfolio = api.get_portfolio_history(date_start=yesterday, date_end=todays_date, timeframe="1Min")





    print(getattr(portfolio, "timestamp"))

    #df = DataFrame.from_dict(portfolio, orient='index').transpose()

    print(portfolio)
    #print(df)
