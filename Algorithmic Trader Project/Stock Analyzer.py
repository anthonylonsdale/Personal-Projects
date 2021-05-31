import time
import os
import yfinance as yf
import pandas as pd
import shutil
import glob
import requests
import alpaca_trade_api as trade_api
import datetime as dt
from clr import AddReference
import csv


def get_tickers(api):
    tickers = []
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    df = table[0]
    sandp500tickers = df['Symbol'].to_list()
    print(sandp500tickers)

    # these headers and params are subject to change in the event NASDAQ changes its API
    headers = {'authority': 'api.nasdaq.com', 'accept': 'application/json, text/plain, */*',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                             ' Chrome/87.0.4280.141 Safari/537.36',
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
    # Drop all stocks with less than 500 million in market cap
    df = df[df.marketCap > 500000000]
    df = df[df.marketCap != 0 & df.marketCap.notnull()]
    # I believe an acceptable level of liquidity is at least 100 shares traded per second avg,
    # which is 2.34 million per normal trading day (6.5 hours)
    df = df[df.volume > 2340000]

    # we should probably test these stocks to see if they are tradeable on alpaca
    for index, iterrow in df.iterrows():
        for i in range(len(sandp500tickers)):
            ticker = iterrow['symbol']
            if ticker == sandp500tickers[i]:
                try:
                    asset = api.get_asset(ticker)
                    print(asset)
                    if asset.tradable and asset.easy_to_borrow and asset.marginable and asset.shortable:
                        tickers.append(ticker)
                except Exception as error:
                    print(error)
                    pass

    return tickers


def api_calls(tickers, parent_dir):
    yfinance_api_calls = 0
    stock_failures = 0
    stocks_not_imported = 0
    i = 0
    while (i < len(tickers)) and (yfinance_api_calls < 1800):
        try:
            ticker = tickers[i]  # Gets the current stock ticker
            temp = yf.Ticker(str(ticker))
            his_data = temp.history(period="max")
            his_data.to_csv(r"{}/ALGO/Daily Stock Analysis/Stocks/{}.csv".format(parent_dir, ticker))
            time.sleep(2)
            yfinance_api_calls += 1
            stock_failures = 0
            i += 1
            print('Number of stocks gathered:', i)
        except ValueError:
            print("Error with gathering Yahoo Finance data for {}".format(str(tickers[i])))
            if stock_failures > 5:
                i += 1
                stocks_not_imported += 1
            yfinance_api_calls += 1
            stock_failures += 1
    print("The amount of stocks we successfully imported: " + str(i - stocks_not_imported))


def obv_score_array(parent_dir):
    list_files = (glob.glob(r"{}/ALGO/Daily Stock Analysis/Stocks/*.csv".format(parent_dir)))
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


class APIbootstrap:
    def __init__(self):
        token_file = open("alpaca_keys.txt")
        keys = token_file.readlines()
        self.api = trade_api.REST(keys[0], keys[1], "https://paper-api.alpaca.markets", api_version='v2')

    def get_tickers(self, *args):
        parent_dir = r"C:/Users/fabio/PycharmProjects/AlgoTrader"

        date_for_obv = dt.datetime.date(dt.datetime.now(dt.timezone.utc))
        print(date_for_obv)
        if os.path.isfile('{}/ALGO/Daily Stock Analysis/{}_OBV_Ranked.csv'.format(parent_dir, date_for_obv)):
            print('OBV data exists for today')
        else:
            try:
                shutil.rmtree("{}/ALGO/Daily Stock Analysis/Stocks".format(parent_dir))
                os.mkdir("{}/ALGO/Daily Stock Analysis/Stocks".format(parent_dir))
            except FileNotFoundError:
                try:
                    os.mkdir("{}/ALGO/Daily Stock Analysis".format(parent_dir))
                except FileExistsError:
                    pass
                os.mkdir("{}/ALGO/Daily Stock Analysis/Stocks".format(parent_dir))

            stock_tickers = get_tickers(self.api)
            api_calls(stock_tickers, parent_dir)
            obv_array = obv_score_array(parent_dir)

            obv_dataframe = pd.DataFrame(obv_array, columns=['Stock', 'OBV_Value'])
            obv_dataframe["Stocks_Ranked"] = obv_dataframe["OBV_Value"].rank(ascending=False)
            obv_dataframe.sort_values("OBV_Value", inplace=True, ascending=False)  # Sort the ranked stocks
            print(obv_dataframe)
            obv_dataframe.to_csv('{}/ALGO/Daily Stock Analysis/{}_OBV_Ranked.csv'.format(parent_dir, date_for_obv),
                                 index=False)

        while True:
            minimum_position = 1.0
            maximum_position = 3.0
            retry = False
            start_reducing = False
            stock_tickers = []
            try:
                if os.path.isfile('{}/ALGO/Daily Stock Analysis/{}_OBV_Ranked.csv'.format(parent_dir,
                                                                                          date_for_obv)):
                    if os.stat('{}/ALGO/Daily Stock Analysis/{}_OBV_Ranked.csv'.format(parent_dir,
                                                                                       date_for_obv)).st_size > 0:
                        with open('{}/ALGO/Daily Stock Analysis/{}_OBV_Ranked.csv'.format(parent_dir, date_for_obv),
                                  'r') as f:
                            reader = csv.reader(f)
                            for position, row in enumerate(reader):
                                if position > 0:
                                    if minimum_position <= position <= maximum_position:
                                        if row[0] not in stock_tickers:
                                            stock_tickers.append(row[0])
                print(stock_tickers)
                AddReference(
                    r"C:\Users\fabio\source\repos\Webscraper Class Library\Webscraper Class Library\bin"
                    r"\Debug\Webscraper Class Library.dll")
                import CSharpwebscraper

                scraper = CSharpwebscraper.Webscraper()
                for position, item in enumerate(stock_tickers):
                    stock = [stock_tickers[position]]
                    try:
                        scraper.Scraper(stock)
                    except Exception as e:
                        print(e, "Error Found with Tickers!")
                        line = stock_tickers[position]
                        lines = []
                        with open('{}/ALGO/Daily Stock Analysis/{}_OBV_Ranked.csv'.format(parent_dir, date_for_obv),
                                  'r') as f:
                            reader = csv.reader(f)
                            for place, row in enumerate(reader):
                                if place > 0:
                                    if row[0] == line:
                                        start_reducing = True
                                        continue
                                    if start_reducing:
                                        row[2] = float(row[2]) - 1
                                    lines.append(row)
                                else:
                                    lines.append(row)
                        with open('{}/ALGO/Daily Stock Analysis/{}_OBV_Ranked.csv'.format(parent_dir, date_for_obv),
                                  'w') as w:
                            writer = csv.writer(w, lineterminator='\n')
                            writer.writerows(lines)
                        retry = True
                        print(stock_tickers)
                if not retry:
                    break
            except Exception as e:
                print(e)
                print("An error with the automated stock fetcher was found")
                break
        return stock_tickers


if __name__ == '__main__':
    Bootstrapper = APIbootstrap()
    Bootstrapper.get_tickers()
