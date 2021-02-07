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
import numpy as np


def orders_to_excel(activities_dataframe, metrics):
    book = openpyxl.load_workbook('Portfolio Data.xlsx')
    writer = pd.ExcelWriter('Portfolio Data.xlsx', engine='openpyxl')
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    activities_dataframe.to_excel(writer, sheet_name='Activities')
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
            stock_url = 'https://finance.yahoo.com/quote/' + stock + '?p=' + stock
            driver.get(stock_url)
            html = driver.execute_script('return document.body.innerHTML;')
            soup = BeautifulSoup(html, 'lxml')
            beta_metric = [entry.text for entry in soup.find_all('span', {'data-reactid': '144'})]
            return_pct = [entry.text for entry in soup.find_all('span', {'data-reactid': '51'})]
            delimiter1 = '('
            delimiter2 = ')'
            formatted_return = str(return_pct[0])
            rt = formatted_return[formatted_return.find(delimiter1) + 1: formatted_return.find(delimiter2)]
            return_string = rt.split("%")[0]
            returns = float(return_string)
            quote['stock'] = stock
            quote['beta'] = beta_metric[0]
            quote['returns'] = round(returns, 4)
            quote_data[stock] = quote
        # spy
        spy_url = 'https://finance.yahoo.com/quote/SPY?p=SPY'
        driver.get(spy_url)
        html = driver.execute_script('return document.body.innerHTML;')
        soup = BeautifulSoup(html, 'lxml')
        spy_returns_pct = [entry.text for entry in soup.find_all('span', {'data-reactid': '51'})]
        delimiter1 = '('
        delimiter2 = ')'
        formatted_return = str(spy_returns_pct[0])
        rt = formatted_return[formatted_return.find(delimiter1) + 1: formatted_return.find(delimiter2)]
        return_string = rt.split("%")[0]
        spy_returns = float(return_string)
        return spy_returns
    except Exception as e:
        print(e)
    finally:
        driver.quit()


def purchasing_filter(activities_df):
    # filtering out bull side long purchases
    long_purchases_df = activities_df.loc[(activities_df['side'] == 'buy') & (activities_df['cumulative_sum'] > 0)]
    total_long_purchases = round(long_purchases_df['net_trade'].sum(), 2)
    print("Gross cost of long positions:", total_long_purchases)

    # filtering out bear side 'buy to cover' purchases
    short_purchases_df = activities_df.loc[(activities_df['side'] == 'buy') & (activities_df['cumulative_sum'] <= 0)]
    total_short_purchases = round(short_purchases_df['net_trade'].sum(), 2)
    print("Gross cost of short positions:", total_short_purchases)

    # filtering bull side long sales
    long_sales_df = activities_df.loc[activities_df['side'] == 'sell']
    total_long_sells = round(long_sales_df['net_trade'].sum(), 2)
    print("Gross profit of long positions:", total_long_sells)

    # filtering bear side short purchases
    short_sales_df = activities_df.loc[activities_df['side'] == 'sell_short']
    total_short_sells = round(short_sales_df['net_trade'].sum(), 2)
    print("Gross profit of short positions:", total_short_sells)

    activities_df.to_excel("Portfolio Activities Test.xlsx")

    long_buy_df = long_purchases_df.sort_values(['symbol', 'transaction_time'])
    lb_df = pd.DataFrame(long_buy_df)
    lb_df.reset_index(drop=True, inplace=True)
    # lb_df.to_excel("test grouping buy.xlsx")
    # print(lb_df)

    long_sales_df = long_sales_df.sort_values(['symbol', 'transaction_time'])
    ls_df = pd.DataFrame(long_sales_df)
    ls_df.reset_index(drop=True, inplace=True)
    # ls_df.to_excel("test grouping sell.xlsx")
    # print(ls_df)

    short_buys_df = short_purchases_df.sort_values(['symbol', 'transaction_time'])
    sb_df = pd.DataFrame(short_buys_df)
    sb_df.reset_index(drop=True, inplace=True)
    # print(sb_df)

    short_sells_df = short_sales_df.sort_values(['symbol', 'transaction_time'])
    ss_df = pd.DataFrame(short_sells_df)
    ss_df.reset_index(drop=True, inplace=True)
    # print(ss_df)
    return lb_df, ls_df, sb_df, ss_df


def order_settlement():
    current_buy_pos = 0
    current_sell_pos = 0
    ###################################################################################################################
    for position, item in enumerate(short_buy_order_book.copy(), start=current_buy_pos):
        try:
            position = current_buy_pos
            i = 1
            buy_qty = short_buy_order_book[current_buy_pos][2]
            buy_value = short_buy_order_book[current_buy_pos][3]
            if short_buy_order_book[current_buy_pos][1] == 'partial_fill':
                while True:
                    if short_buy_order_book[current_buy_pos + i][1] == 'partial_fill':
                        buy_qty += short_buy_order_book[current_buy_pos + i][2]
                        buy_value += short_buy_order_book[current_buy_pos + i][3]
                        i += 1
                    else:
                        buy_qty += short_buy_order_book[current_buy_pos + i][2]
                        buy_value += short_buy_order_book[current_buy_pos + i][3]
                        short_buy_order_book[current_buy_pos + i][2] = buy_qty
                        short_buy_order_book[current_buy_pos + i][3] = round(buy_value, 2)
                        for j in range(i):
                            del short_buy_order_book[current_buy_pos + j]
                        break
            current_buy_pos += i
            position += i
        except KeyError:
            pass
    print(len(short_buy_order_book), short_buy_order_book)

    for position, item in enumerate(short_sell_order_book.copy(), start=current_sell_pos):
        try:
            position = current_sell_pos
            i = 1
            buy_qty = short_sell_order_book[current_sell_pos][2]
            buy_value = short_sell_order_book[current_sell_pos][3]
            if short_sell_order_book[current_sell_pos][1] == 'partial_fill':
                while True:
                    if short_sell_order_book[current_sell_pos + i][1] == 'partial_fill':
                        buy_qty += short_sell_order_book[current_sell_pos + i][2]
                        buy_value += short_sell_order_book[current_sell_pos + i][3]
                        i += 1
                    else:
                        buy_qty += short_sell_order_book[current_sell_pos + i][2]
                        buy_value += short_sell_order_book[current_sell_pos + i][3]
                        short_sell_order_book[current_sell_pos + i][2] = buy_qty
                        short_sell_order_book[current_sell_pos + i][3] = round(buy_value, 2)
                        for j in range(i):
                            del short_sell_order_book[current_sell_pos + j]
                        break
            current_sell_pos += i
            position += i
        except KeyError:
            pass
    print(len(short_sell_order_book), short_sell_order_book)

    current_buy_pos = 0
    current_sell_pos = 0
    for position, item in enumerate(buy_order_book.copy(), start=current_buy_pos):
        try:
            position = current_buy_pos
            i = 1
            buy_qty = buy_order_book[current_buy_pos][2]
            buy_value = buy_order_book[current_buy_pos][3]
            if buy_order_book[current_buy_pos][1] == 'partial_fill':
                while True:
                    if buy_order_book[current_buy_pos + i][1] == 'partial_fill':
                        buy_qty += buy_order_book[current_buy_pos + i][2]
                        buy_value += buy_order_book[current_buy_pos + i][3]
                        i += 1
                    else:
                        buy_qty += buy_order_book[current_buy_pos + i][2]
                        buy_value += buy_order_book[current_buy_pos + i][3]
                        buy_order_book[current_buy_pos + i][2] = buy_qty
                        buy_order_book[current_buy_pos + i][3] = round(buy_value, 2)
                        for j in range(i):
                            del buy_order_book[current_buy_pos + j]
                        break
            current_buy_pos += i
            position += i
        except KeyError:
            pass
    print(len(buy_order_book), buy_order_book)

    for position, item in enumerate(sell_order_book.copy(), start=current_sell_pos):
        try:
            position = current_sell_pos
            i = 1
            sell_qty = sell_order_book[current_sell_pos][2]
            sell_value = sell_order_book[current_sell_pos][3]
            if sell_order_book[current_sell_pos][1] == 'partial_fill':
                while True:
                    if sell_order_book[current_sell_pos + i][1] == 'partial_fill':
                        sell_qty += sell_order_book[current_sell_pos + i][2]
                        sell_value += sell_order_book[current_sell_pos + i][3]
                        i += 1
                    else:
                        sell_qty += sell_order_book[current_sell_pos + i][2]
                        sell_value += sell_order_book[current_sell_pos + i][3]
                        sell_order_book[current_sell_pos + i][2] = sell_qty
                        sell_order_book[current_sell_pos + i][3] = round(sell_value, 2)
                        for j in range(i):
                            del sell_order_book[current_sell_pos + j]
                        break
            current_sell_pos += i
            position += i
        except KeyError:
            pass
    print(len(sell_order_book), sell_order_book)


def trade_book_settlement():
    trade_book = {}
    short_trade_book = {}
    ####################################################################################################################
    # adding to respective trade books
    current_buy_pos = 0
    current_sell_pos = 0
    short_trade_ledger_position = 0

    while len(short_buy_order_book) > 0:
        for position, item in enumerate(short_buy_order_book.copy(), start=current_buy_pos):
            if short_buy_order_book[current_buy_pos][2] == short_sell_order_book[current_sell_pos][2]:
                short_trade_book[short_trade_ledger_position] = round(short_buy_order_book[current_buy_pos][3] +
                                                                      short_sell_order_book[current_sell_pos][3], 2)
                del short_buy_order_book[current_buy_pos], short_sell_order_book[current_sell_pos]

            else:
                while True:
                    bought_share_value = round(
                        short_buy_order_book[current_buy_pos][3] / short_buy_order_book[current_buy_pos][2], 2)
                    sold_share_value = round(
                        short_sell_order_book[current_sell_pos][3] / short_sell_order_book[current_sell_pos][2], 2)
                    buy_quantity = short_buy_order_book[current_buy_pos][2]
                    sell_quantity = short_sell_order_book[current_sell_pos][2]
                    buy_val = short_buy_order_book[current_buy_pos][3]
                    sell_val = short_sell_order_book[current_sell_pos][3]

                    if buy_quantity > sell_quantity:
                        value_of_shares_sold = bought_share_value * sell_quantity
                        short_trade_book[short_trade_ledger_position] = round(value_of_shares_sold + sell_val, 2)
                        short_buy_order_book[current_buy_pos][2] -= sell_quantity
                        short_buy_order_book[current_buy_pos][3] = round(buy_val - value_of_shares_sold, 2)
                        short_buy_order_book[current_buy_pos][4] -= sell_quantity
                        del short_sell_order_book[current_sell_pos]
                        break

                    if buy_quantity < sell_quantity:
                        value_of_shares_sold = sold_share_value * buy_quantity
                        short_sell_order_book[current_sell_pos][2] -= buy_quantity
                        short_sell_order_book[current_sell_pos][3] = round(sell_val - value_of_shares_sold, 2)
                        del short_buy_order_book[current_buy_pos]
                        short_trade_book[short_trade_ledger_position] = round(value_of_shares_sold + buy_val, 2)
                    break

            if len(short_buy_order_book) > 0:
                current_buy_pos = list(short_buy_order_book)[0]
                current_sell_pos = list(short_sell_order_book)[0]
                short_trade_ledger_position += 1

    current_buy_pos = 0
    current_sell_pos = 0
    trade_ledger_position = 0

    while len(buy_order_book) > 0:
        for position, item in enumerate(buy_order_book.copy(), start=current_buy_pos):
            if buy_order_book[current_buy_pos][2] == sell_order_book[current_sell_pos][2]:
                trade_book[trade_ledger_position] = round(buy_order_book[current_buy_pos][3] +
                                                          sell_order_book[current_sell_pos][3], 2)
                del buy_order_book[current_buy_pos], sell_order_book[current_sell_pos]

            else:
                while True:
                    bought_share_value = round(buy_order_book[current_buy_pos][3] / buy_order_book[current_buy_pos][2],
                                               2)
                    sold_share_value = round(
                        sell_order_book[current_sell_pos][3] / sell_order_book[current_sell_pos][2], 2)
                    buy_quantity = buy_order_book[current_buy_pos][2]
                    sell_quantity = sell_order_book[current_sell_pos][2]
                    buy_val = buy_order_book[current_buy_pos][3]
                    sell_val = sell_order_book[current_sell_pos][3]

                    if buy_quantity > sell_quantity:
                        value_of_shares_sold = bought_share_value * sell_quantity
                        trade_book[trade_ledger_position] = round(value_of_shares_sold + sell_val, 2)
                        buy_order_book[current_buy_pos][2] -= sell_quantity
                        buy_order_book[current_buy_pos][3] = round(buy_val - value_of_shares_sold, 2)
                        buy_order_book[current_buy_pos][4] -= sell_quantity
                        del sell_order_book[current_sell_pos]
                        break

                    if buy_quantity < sell_quantity:
                        value_of_shares_sold = sold_share_value * buy_quantity
                        sell_order_book[current_sell_pos][2] -= buy_quantity
                        sell_order_book[current_sell_pos][3] = round(sell_val - value_of_shares_sold, 2)
                        del buy_order_book[current_buy_pos]
                        trade_book[trade_ledger_position] = round(value_of_shares_sold + buy_val, 2)
                    break

            if len(buy_order_book) > 0:
                current_buy_pos = list(buy_order_book)[0]
                current_sell_pos = list(sell_order_book)[0]
                trade_ledger_position += 1

    return short_trade_book, trade_book


if __name__ == '__main__':
    if not os.path.isfile(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Portfolio Data.xlsx"):
        wb = openpyxl.Workbook()
        wb.save('Portfolio Data.xlsx')

    pd.options.mode.chained_assignment = None
    key = "PKCPC6RJ84BG84W3PB60"
    sec = "U1r9Z2QknL9FwAaTztfLl5g1DTxpa5m97qyWCGZ7"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')

    # Can also limit the results by date if desired.
    spec_date = dt.datetime.today() - dt.timedelta(days=29)
    date = spec_date.strftime('%Y-%m-%d')
    activities = api.get_activities(activity_types='FILL', date=date)
    activities_df = pd.DataFrame([activity._raw for activity in activities])
    activities_df = activities_df.iloc[::-1]

    activities_df[['price', 'qty']] = activities_df[['price', 'qty']].apply(pd.to_numeric)
    activities_df['net_qty'] = np.where(activities_df.side == 'buy', activities_df.qty, -activities_df.qty)
    activities_df['net_trade'] = -activities_df.net_qty * activities_df.price
    activities_df.to_excel("Portfolio Activities.xlsx")
    # print(activities_df)
    ###################################################################################################################
    activities_df['cumulative_sum'] = activities_df.groupby('symbol')['net_qty'].apply(lambda g: g.cumsum())

    # Total Net Profit for Long and Short Trades
    lb_df, ls_df, sb_df, ss_df = purchasing_filter(activities_df)

    ###################################################################################################################
    # we can make an order book that tracks each trade as it iterates down the list
    short_buy_order_book = {}
    for index, row in sb_df.iterrows():
        short_buy_order_book[index] = [row['transaction_time'], row['type'], row['qty'], round(row['net_trade'], 2),
                                       row['cumulative_sum']]
    print("short buys", len(short_buy_order_book), short_buy_order_book)
    short_sell_order_book = {}
    for index, row in ss_df.iterrows():
        short_sell_order_book[index] = [row['transaction_time'], row['type'], row['qty'], round(row['net_trade'], 2),
                                        row['cumulative_sum']]
    print("short sells", len(short_sell_order_book), short_sell_order_book)

    buy_order_book = {}
    for index, row in lb_df.iterrows():
        buy_order_book[index] = [row['transaction_time'], row['type'], row['qty'], round(row['net_trade'], 2),
                                 row['cumulative_sum']]
    print("long buys", len(buy_order_book), buy_order_book)

    sell_order_book = {}
    for index, row in ls_df.iterrows():
        sell_order_book[index] = [row['transaction_time'], row['type'], row['qty'], round(row['net_trade'], 2),
                                  row['cumulative_sum']]
    print("long sells", len(sell_order_book), sell_order_book)

    order_settlement()

    short_trades, long_trades = trade_book_settlement()

    ###################################################################################################################
    total_gross_profit = 0
    total_gross_loss = 0

    # initialization of short variables
    short_gross_profit = 0
    short_gross_loss = 0
    net_short_profit = 0
    total_short_trades = 0
    short_winning_trades = 0
    short_even_trades = 0
    short_losing_trades = 0
    for i in range(len(short_trades)):
        if short_trades[i] > 0:
            short_winning_trades += 1
            short_gross_profit += short_trades[i]
            total_gross_profit += short_trades[i]
        elif short_trades[i] < 0:
            short_losing_trades += 1
            short_gross_loss += short_trades[i]
            total_gross_loss += short_trades[i]
        else:
            short_even_trades += 1
        total_short_trades += 1
        net_short_profit += short_trades[i]
    net_short_profit = round(net_short_profit, 2)
    print("Short-side net profit:", net_short_profit)
    print("Short-side profitable trades:", short_winning_trades)
    print("Short-side even trades:", short_even_trades)
    print("Short-side Losing trades:", short_losing_trades)
    print("Total short-side trades:", total_short_trades)

    # initialization of long variables
    long_gross_profit = 0
    long_gross_loss = 0
    net_long_profit = 0
    total_long_trades = 0
    long_winning_trades = 0
    long_even_trades = 0
    long_losing_trades = 0
    for i in range(len(long_trades)):
        if long_trades[i] > 0:
            long_winning_trades += 1
            long_gross_profit += long_trades[i]
            total_gross_profit += long_trades[i]
        elif long_trades[i] < 0:
            long_losing_trades += 1
            long_gross_loss += long_trades[i]
            total_gross_loss += long_trades[i]
        else:
            long_even_trades += 1
        total_long_trades += 1
        net_long_profit += long_trades[i]
    net_long_profit = round(net_long_profit, 2)
    print("\nLong-side net profit:", net_long_profit)
    print("Long-side profitable trades:", long_winning_trades)
    print("Long-side even trades:", long_even_trades)
    print("Long-side losing trades:", long_losing_trades)
    print("Total long-side trades", total_long_trades)

    avg_winning_trade = round((total_gross_profit / (long_winning_trades + short_winning_trades)), 2)
    avg_losing_trade = round((total_gross_loss / (total_long_trades + short_losing_trades)), 2)
    todayspandl = round(total_gross_profit + total_gross_loss, 2)
    total_gross_profit = round(total_gross_profit, 2)
    total_gross_loss = round(total_gross_loss, 2)
    print("\nProfit Metrics:")
    print("Gross Profit:", total_gross_profit)
    print("Average Winning Trade:", avg_winning_trade)
    print("Gross Loss:", total_gross_loss)
    print("Average Losing Trade:", avg_losing_trade)
    print("Total Net Profit:", todayspandl)

    # profit per symbol
    net_zero_trades = activities_df.groupby('symbol').filter(lambda trades: sum(trades.net_qty) == 0)
    trades = net_zero_trades.groupby('symbol').net_trade
    profit_per_symbol = net_zero_trades.groupby('symbol').net_trade.sum()
    print("Net Profit per stock:")
    print(profit_per_symbol)

    stock_tickers_involved = profit_per_symbol.index.tolist()
    print(stock_tickers_involved)

    # for stock in stock_tickers_involved:
        # print(profit_per_symbol[stock])
    #############################################################################
    # the risk free rate is commonly considered to be the interest rate on a 3-month US treasury bond
    threemonthriskfreerate = 0.03
    #############################################################################
    pd.options.display.float_format = '{:.0f}'.format
    driver = webdriver.Chrome(ChromeDriverManager().install())
    quote_data = {}
    for stock in stock_tickers_involved:
        quote_data[stock] = []

    #########################################################################################
    # for quick debugging
    quote_data = {'MSFT': {'stock': 'MSFT', 'beta': '0.82', 'returns': 0.08},
                  'AMZN': {'stock': 'AMZN', 'beta': '1.14', 'returns': 0.63},
                  'AMD': {'stock': 'AMD', 'beta': '2.20', 'returns': 0.07},
                  'AAPL': {'stock': 'AAPL', 'beta': '1.27', 'returns': -0.31}}
    spyreturn = 0.39
    # spyreturn = webscraping(stock_tickers_involved)
    # spyreturn = '{:.4f}'.format(spyreturn)
    # spyreturn = float(spyreturn)
    print(quote_data)
    print(spyreturn)
    #############################################################################
    account = api.get_account()

    print("Daily return of the SPDR S&P 500 ETF Trust ($SPY):", str(spyreturn) + str('%'))
    for stock in stock_tickers_involved:
        # print(quote_data[stock])
        # print(quote_data[stock]['beta'])
        trade_size_relative_to_portfolio = 0.1
        beta = trade_size_relative_to_portfolio * float(quote_data[stock]['beta'])
        buying_power = float(account.buying_power) / 4
        stock_profit_pct = round((profit_per_symbol[stock] / buying_power) * 100, 4)
        print(stock_profit_pct)
        # portfolioreturnpct = (stock_profit / buying_power) * 100
        print(buying_power)
        market_returns_pct = quote_data[stock]['returns']
        alpha = round((stock_profit_pct - threemonthriskfreerate) - (beta * (spyreturn - threemonthriskfreerate)), 4)
        print("Daily percentage performance of {}:".format(stock), str(market_returns_pct) + str('%'))
        print("Daily percentage performance of {} relative to $SPY".format(stock), str(market_returns_pct - spyreturn) + str('%'))
        print("Daily trading performance of {} relative to $SPY and risk-free rate (Alpha):".format(stock), str(alpha) + str('%'))

    total_profit_factor = round((total_gross_profit / total_gross_loss), 2)
    long_profit_factor = round((long_gross_profit / long_gross_loss), 2)
    short_profit_factor = round((short_gross_profit / short_gross_loss), 2)
    total_percent_profitable = round(((long_winning_trades + short_winning_trades) / (total_long_trades + total_short_trades)) * 100, 2)
    long_percent_profitable = round((long_winning_trades / total_long_trades) * 100, 2)
    short_percent_profitable = round((short_winning_trades / total_short_trades) * 100, 2)
    data = [
        ['', 'All Trades', 'Long Trades', 'Short Trades'],
        ['Total Net Profit:', todayspandl, net_long_profit, net_short_profit],
        ['Gross Profit:', total_gross_profit, long_gross_profit, short_gross_profit],
        ['Gross Loss:', total_gross_loss, long_gross_loss, short_gross_loss],
        ['Profit Factor:', total_profit_factor, long_profit_factor, short_profit_factor],
        ['', '', '', ''],
        ['Total Number of Trades:', int(total_long_trades + total_short_trades), total_long_trades, total_short_trades],
        ['Percent Profitable:', str(total_percent_profitable) + str("%"), str(long_percent_profitable) + str('%'),
         str(short_percent_profitable) + str('%')],
        ['Winning Trades:', long_winning_trades + short_winning_trades, long_winning_trades, short_winning_trades],
        ['Losing Trades:', long_losing_trades + short_losing_trades, long_losing_trades, short_losing_trades],
        ['Even Trades', long_even_trades + short_even_trades, long_even_trades, short_even_trades]
            ]
    portfolio_metrics = DataFrame(data, columns=['', 'All Trades', 'Long Trades', 'Short Trades'])

    orders_to_excel(activities_df, portfolio_metrics)
    formatting_excel()
