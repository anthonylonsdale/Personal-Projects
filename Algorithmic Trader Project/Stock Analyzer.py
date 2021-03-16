# updated to full functionality

import time
import os
import yfinance as yf
import pandas as pd
import shutil
import glob
import requests
import openpyxl
import alpaca_trade_api as trade_api


def get_tickers():
    tickers = []
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    df = table[0]
    sandp500tickers = df['Symbol'].to_list()
    print(sandp500tickers)

    # these headers and params are subject to change in the event NASDAQ changes its API
    headers = {'authority': 'api.nasdaq.com', 'accept': 'application/json, text/plain, */*',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
               'origin': 'https://www.nasdaq.com', 'sec-fetch-site': 'same-site', 'sec-fetch-mode': 'cors',
               'sec-fetch-dest': 'empty', 'referer': 'https://www.nasdaq.com/', 'accept-language': 'en-US,en;q=0.9', }
    params = (('tableonly', 'true'), ('limit', '25'), ('offset', '0'), ('download', 'true'),)
    r = requests.get('https://api.nasdaq.com/api/screener/stocks', headers=headers, params=params)
    data = r.json()['data']
    df = pd.DataFrame(data['rows'], columns=data['headers'])

    # Drop all non United States Stocks
    df = df[df.country == 'United States']
    df['marketCap'] = pd.to_numeric(df['marketCap'])
    df['volume'] = pd.to_numeric(df['volume'])
    # Drop all stocks with less than 500 million in market cap and more than 2 trillion
    df = df[df.marketCap > 500000000]
    df = df[df.marketCap != 0 & df.marketCap.notnull()]
    # I believe an acceptable level of liquidity is at least 100 shares traded per second avg,
    # which is 2.34 million per normal trading day (6.5 hours)
    df = df[df.volume > 2340000]

    # we should probably test these stocks to see if they are tradable on alpaca
    for index, row in df.iterrows():
        for i in range(len(sandp500tickers)):
            stock = row['symbol']
            if stock == sandp500tickers[i]:
                try:
                    asset = api.get_asset(stock)
                    print(asset)
                    if asset.tradable and asset.easy_to_borrow and asset.marginable and asset.shortable:
                        tickers.append(stock)
                except Exception as e:
                    print(e)
                    pass

    book = openpyxl.load_workbook('Ticker Selections.xlsx')
    writer = pd.ExcelWriter('Ticker Selections.xlsx', engine='openpyxl')
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    df.to_excel(writer)
    book.save('Ticker Selections.xlsx')
    writer.save()

    print(tickers)
    print(len(tickers))
    return tickers


def api_calls():
    api_calls = 0
    stock_failures = 0
    stocks_not_imported = 0
    i = 0
    while (i < len(tickers)) and (api_calls < 1800):
        try:
            stock = tickers[i]  # Gets the current stock ticker
            temp = yf.Ticker(str(stock))
            his_data = temp.history(period="max")
            his_data.to_csv(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Daily Stock Analysis\Stocks\\" + stock + ".csv")
            time.sleep(2)
            api_calls += 1
            stock_failures = 0
            i += 1
            print('Number of stocks gathered:', i)
        except ValueError:
            print("Error with gathering Yahoo Finance data for {}".format(str(tickers[i])))
            if stock_failures > 5:
                i += 1
                stocks_not_imported += 1
            api_calls += 1
            stock_failures += 1
    print("The amount of stocks we successfully imported: " + str(i - stocks_not_imported))


def obv_score_array():
    list_files = (glob.glob(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Daily Stock Analysis\Stocks\\*.csv"))
    new_data = []  # This will be a 2D array to hold our stock name and OBV score
    interval = 0  # Used for iteration
    while interval < len(list_files):
        data = pd.read_csv(list_files[interval]).tail(7)  # Gets the last 7 days of trading for the current stock
        pos_move = []  # List of days that the stock price increased
        neg_move = []  # List of days that the stock price increased
        obv_value = 0  # Sets the initial OBV_Value to zero
        count = 0
        while count < 7:  # 7 because we are looking at the last 7 trading days
            if data.iloc[count, 1] < data.iloc[count, 4]:  # True if the stock increased in price
                pos_move.append(count)  # Add the day to the pos_move list
            elif data.iloc[count, 1] > data.iloc[count, 4]:  # True if the stock decreased in price
                neg_move.append(count)  # Add the day to the neg_move list
            count += 1
        for i in pos_move:  # Adds the volumes of positive days to OBV_Value, divide by opening price to normalize
            obv_value = round(obv_value + (data.iloc[i, 5] / data.iloc[i, 1]))
        for i in neg_move:  # Subtracts the volumes of negative days from OBV_Value, divide by opening price
            obv_value = round(obv_value - (data.iloc[i, 5] / data.iloc[i, 1]))
        stock_name = ((os.path.basename(list_files[interval])).split(".csv")[0])  # Get the name of the current stock
        new_data.append([stock_name, obv_value])  # Add the stock name and OBV value to the new_data list
        interval += 1
    return new_data


if __name__ == '__main__':
    if not os.path.isfile(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Ticker Selections.xlsx"):
        wb = openpyxl.Workbook()
        wb.save('Ticker Selections.xlsx')

    try:
        shutil.rmtree(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Daily Stock Analysis\Stocks")
    except Exception as e:
        print(e)
        pass
    os.mkdir(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Daily Stock Analysis\Stocks")
    ###################################################################################################################
    key = "PKCPC6RJ84BG84W3PB60"
    sec = "U1r9Z2QknL9FwAaTztfLl5g1DTxpa5m97qyWCGZ7"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')
    ###################################################################################################################
    tickers = get_tickers()
    api_calls()
    obv_score_array = obv_score_array()
    ###################################################################################################################
    df = pd.DataFrame(obv_score_array, columns=['Stock', 'OBV_Value'])
    df["Stocks_Ranked"] = df["OBV_Value"].rank(ascending=False)  # Rank the stocks by their OBV_Values
    df.sort_values("OBV_Value", inplace=True, ascending=False)  # Sort the ranked stocks
    print(df)
    df.to_csv(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Daily Stock Analysis\OBV_Ranked.csv", index=False)
