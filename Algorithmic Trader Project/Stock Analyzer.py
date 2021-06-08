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


def get_tickers(tickers, api):
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    df = table[0]
    sandp500tickers = df['Symbol'].to_list()

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


def api_calls(tickers):
    data = yf.download(tickers=tickers, threads=True, group_by='ticker', period="1mo")
    data = data.round(decimals=2)

    # drops invalid stocks
    data = data.dropna(how='all', axis=0)

    for i in tickers:
        data[i].to_csv(f'../ALGO/Daily Stock Analysis/Stocks/{i}.csv')


def obv_score_array(stock_tickers):
    list_files = glob.glob(r"../ALGO/Daily Stock Analysis/Stocks/*.csv")

    # MFM = (Close - Low) - (High - Close) / (High - Low)
    # Money Flow Volume = MFM * Day Volume
    # Accumulation/ Distribution = Previous A/d + MFV
    # this multiplier provides a gauge for how strong the buying or selling was during a particular period
    # the highest rated stocks do not seem to perform the best, but they do seem to have the highest
    # volatility, which is good for our purposes. This represents an improvement over OBV

    new_data = []
    for i in range(len(list_files)):
        data = pd.read_csv(list_files[i]).tail(7)

        accumulationdistribution = 0
        for j in range(7):
            open = data.iloc[j, 1]
            high = data.iloc[j, 2]
            low = data.iloc[j, 3]
            close = data.iloc[j, 4]
            volume = data.iloc[j, 6]
            
            # divide by the open price to normalize it, that way accum/dist is reflective of money instead of 
            # number of shares
            mfm = (((close - low) - (high - close)) / (high - low)) / open
            
            if close > open:
                accumulationdistribution += round(mfm * volume)
            if close < open:
                accumulationdistribution -= round(mfm * volume)
        new_data.append([stock_tickers[i], accumulationdistribution])
    return new_data


class APIbootstrap:
    def __init__(self):
        token_file = open("alpaca_keys.txt")
        keys = token_file.readlines()
        key = keys[0].rstrip('\n')
        sec_key = keys[1].rstrip('\n')
        self._api = trade_api.REST(key, sec_key, base_url=trade_api.stream.URL("https://paper-api.alpaca.markets"),
                                   api_version='v2')
        self._pruned_tickers = []
        self._file_date = dt.datetime.date(dt.datetime.now())
        self._file_name = f'../ALGO/Daily Stock Analysis/{self._file_date}_ACC_DIST_Ranked.csv'
        self._stocks_folder = "../ALGO/Daily Stock Analysis/Stocks"

    def get_tickers(self):
        if os.path.isfile(self._file_name):
            print('OBV data exists for today')
        else:
            try:
                shutil.rmtree(self._stocks_folder)
                os.mkdir(self._stocks_folder)
            except FileNotFoundError:
                try:
                    os.mkdir("../ALGO/Daily Stock Analysis")
                except FileExistsError:
                    pass
                os.mkdir(self._stocks_folder)

            stock_tickers = get_tickers(self._pruned_tickers, self._api)
            api_calls(stock_tickers)
            accum_dist_array = obv_score_array(stock_tickers)

            accum_dist_df = pd.DataFrame(accum_dist_array, columns=['Stock', 'Accumulation/Distribution Value'])
            accum_dist_df["Stocks_Ranked"] = accum_dist_df['Accumulation/Distribution Value'].rank(ascending=False)
            accum_dist_df.sort_values('Accumulation/Distribution Value', inplace=True, ascending=False)
            accum_dist_df.to_csv(self._file_name, index=False)
            print(accum_dist_df)
        while True:
            minimum_position = 1.0
            maximum_position = 3.0
            retry = False
            start_reducing = False
            stock_tickers = []
            try:
                if os.path.isfile(self._file_name):
                    if os.stat(self._file_name).st_size > 0:
                        with open(self._file_name, 'r') as f:
                            reader = csv.reader(f)
                            for position, row in enumerate(reader):
                                if position > 0:
                                    if minimum_position <= position <= maximum_position:
                                        if row[0] not in stock_tickers:
                                            stock_tickers.append(row[0])
                print(stock_tickers)
                AddReference(r"C:\Users\fabio\source\repos\Webscraper Class Library\Webscraper Class Library\bin\Debug"
                             r"\Webscraper Class Library.dll")
                import CSharpwebscraper

                scraper = CSharpwebscraper.Webscraper()
                for stock in stock_tickers:
                    try:
                        scraper.Scraper([stock])
                    except Exception as e:
                        print(e, "Error Found with Tickers!")
                        line = stock
                        lines = []
                        with open(self._file_name, 'r') as f:
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

                        with open(self._file_name, 'w') as w:
                            writer = csv.writer(w, lineterminator='\n')
                            writer.writerows(lines)
                        retry = True
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
