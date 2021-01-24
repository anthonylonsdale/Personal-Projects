# to be combined with the other portfolio analysis program
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
import numpy as np


if __name__ == '__main__':
    pd.options.mode.chained_assignment = None
    key = "PKCPC6RJ84BG84W3PB60"
    sec = "U1r9Z2QknL9FwAaTztfLl5g1DTxpa5m97qyWCGZ7"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')
    # Get a list of filled orders.
    # Can also limit the results by date if desired.

    spec_date = dt.datetime.today() - dt.timedelta(days=15)
    date = spec_date.strftime('%Y-%m-%d')
    activities = api.get_activities(activity_types='FILL', date=date)
    # Turn the activities list into a dataframe for easier manipulation
    activities_df = pd.DataFrame([activity._raw for activity in activities])
    activities_df = activities_df.iloc[::-1]
    stock_tickers_involved = list(set(activities_df['symbol'].tolist()))
    print(stock_tickers_involved)

    activities_df[['price', 'qty']] = activities_df[['price', 'qty']].apply(pd.to_numeric)
    activities_df['net_qty'] = np.where(activities_df.side == 'buy', activities_df.qty, -activities_df.qty)
    activities_df['net_trade'] = -activities_df.net_qty * activities_df.price
    activities_df.to_excel("Portfolio Activities.xlsx")
    print(activities_df)
    ###################################################################################################################
    activities_df['cumulative_sum'] = activities_df.groupby('symbol')['net_qty'].apply(lambda g: g.cumsum())

    # filtering out bull long purchases
    long_purchases = activities_df.loc[(activities_df['side'] == 'buy') & (activities_df['cumulative_sum'] > 0)]
    # print(long_purchases)
    # long_purchases.to_excel("long purchases.xlsx")
    total_long_purchases = long_purchases['net_trade'].sum()
    print("Total cost of long positions:", total_long_purchases)

    # filtering out bear 'buy to cover' purchases
    short_purchases = activities_df.loc[(activities_df['side'] == 'buy') & (activities_df['cumulative_sum'] <= 0)]
    # print(short_purchases)
    # short_purchases.to_excel("short purchases.xlsx")
    total_short_purchases = short_purchases['net_trade'].sum()
    print("Total cost of short positions:", total_short_purchases)

    # filtering bull long sales
    long_sales = activities_df.loc[activities_df['side'] == 'sell']
    # print(long_sales)
    # long_sales.to_excel("long sales.xlsx")
    total_long_sells = long_sales['net_trade'].sum()
    print("Total profit of long positions:", total_long_sells)

    # filtering bear short purchases
    short_sales = activities_df.loc[activities_df['side'] == 'sell_short']
    # print(short_sales)
    # short_sales.to_excel("short sales.xlsx")
    total_short_sells = short_sales['net_trade'].sum()
    print("Total profit of short positions:", total_short_sells)

    long_position_pl = round(total_long_purchases + total_long_sells, 2)
    short_position_pl = round(total_short_purchases + total_short_sells, 2)
    print(long_position_pl)
    print(short_position_pl)


    activities_df.to_excel("Portfolio Activities Test.xlsx")
    ###################################################################################################################
    # profit per symbol
    net_zero_trades = activities_df.groupby('symbol').filter(lambda trades: sum(trades.net_qty) == 0)
    trades = net_zero_trades.groupby('symbol').net_trade
    profit_per_symbol = net_zero_trades.groupby('symbol').net_trade.sum()
    print(profit_per_symbol)
