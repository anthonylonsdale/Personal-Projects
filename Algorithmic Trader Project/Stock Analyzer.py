import time
import os
import yfinance as yf
import pandas as pd
import shutil
import glob
from get_all_tickers import get_tickers as gt


def get_tickers():
    # gathers all s&p 500 components
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    df = table[0]
    spytickers = df['Symbol'].to_list()

    # mkt cap is in millions
    # so we are looking from 10 billion (for sufficient volume) to 25 billion
    minmktcap = 15000
    maxmktcap = 20000
    tickers = gt.get_tickers_filtered(mktcap_min=minmktcap, mktcap_max=maxmktcap)
    # Check that the amount of tickers isn't more than 1800
    while len(tickers) > 1800:
        print('The number of stocks between a market cap of ${} million and ${} million is too high, enter new'
              'market cap parameters:')
        minmktcap = int(input('Minimum market cap (in millions):'))
        maxmktcap = int(input('Minimum market cap (in millions):'))
        tickers = gt.get_tickers_filtered(mktcap_min=minmktcap, mktcap_max=maxmktcap)
    print("Number of stocks with a market cap between ${} million and ${} million: ".format(minmktcap, maxmktcap) +
          str(len(tickers)))
    # we only want to use tickers in the s and p 500
    tickerlist = []
    for ticker in spytickers:
        if ticker in tickers:
            tickerlist.append(ticker)
    print(len(tickerlist))
    return tickerlist


def api_calls():
    API_Calls = 0
    stock_failures = 0
    Stocks_Not_Imported = 0
    i = 0
    while (i < len(tickers)) and (API_Calls < 1800):
        try:
            stock = tickers[i]  # Gets the current stock ticker
            temp = yf.Ticker(str(stock))
            Hist_data = temp.history(period="max")
            Hist_data.to_csv(
                r"C:\Users\fabio\PycharmProjects\AlgoTrader\Daily Stock Analysis\Stocks\\" + stock + ".csv")
            time.sleep(2)
            API_Calls += 1
            stock_failures = 0
            i += 1
            print('Number of stocks gathered:', i)
        except ValueError:
            print("Error with gathering Yahoo Finance data for {}".format(str(tickers[i])))
            if stock_failures > 5:
                i += 1
                Stocks_Not_Imported += 1
            API_Calls += 1
            stock_failures += 1
    print("The amount of stocks we successfully imported: " + str(i - Stocks_Not_Imported))


def obv_score_array():
    list_files = (glob.glob(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Daily Stock Analysis\Stocks\\*.csv"))
    new_data = []  # This will be a 2D array to hold our stock name and OBV score
    interval = 0  # Used for iteration
    while interval < len(list_files):
        Data = pd.read_csv(list_files[interval]).tail(7)  # Gets the last 7 days of trading for the current stock in iteration
        pos_move = []  # List of days that the stock price increased
        neg_move = []  # List of days that the stock price increased
        OBV_Value = 0  # Sets the initial OBV_Value to zero
        count = 0
        while (count < 7):  # 10 because we are looking at the last 7 trading days
            if Data.iloc[count, 1] < Data.iloc[count, 4]:  # True if the stock increased in price
                pos_move.append(count)  # Add the day to the pos_move list
            elif Data.iloc[count, 1] > Data.iloc[count, 4]:  # True if the stock decreased in price
                neg_move.append(count)  # Add the day to the neg_move list
            count += 1
        for i in pos_move:  # Adds the volumes of positive days to OBV_Value, divide by opening price to normalize across all stocks
            OBV_Value = round(OBV_Value + (Data.iloc[i, 5] / Data.iloc[i, 1]))
        for i in neg_move:  # Subtracts the volumes of negative days from OBV_Value, divide by opening price to normalize across all stocks
            OBV_Value = round(OBV_Value - (Data.iloc[i, 5] / Data.iloc[i, 1]))
        Stock_Name = ((os.path.basename(list_files[interval])).split(".csv")[0])  # Get the name of the current stock
        new_data.append([Stock_Name, OBV_Value])  # Add the stock name and OBV value to the new_data list
        interval += 1
    return new_data


if __name__ == '__main__':
    try:
        shutil.rmtree(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Daily Stock Analysis\Stocks")
    except Exception:
        pass
    os.mkdir(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Daily Stock Analysis\Stocks")
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
