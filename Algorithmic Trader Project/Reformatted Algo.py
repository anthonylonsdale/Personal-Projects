# updated to full functionality

import pandas as pd
import requests
from win10toast import ToastNotifier
import alpaca_trade_api as trade_api
from alpaca_trade_api.stream import URL
from pandas import DataFrame
import openpyxl
import win32com.client as win32
import os
from bs4 import BeautifulSoup
import numpy as np
import sys
import concurrent.futures
import datetime as dt
import time
import threading as th

from ALGO.stock_init_fetch_module import APIbootstrap
from ALGO.websocket_core_module import WebsocketBootStrapper
from ALGO.stock_data_module import stockDataEngine
from ALGO.technical_indicators_core import technicalIndicators
from ALGO.bond_yield_fetch import riskfreerate
from ALGO.options_module import Options


def data_to_excel(metrics):
    book = openpyxl.load_workbook('Portfolio Data.xlsx')
    excel_writer = pd.ExcelWriter('Portfolio Data.xlsx', engine='openpyxl')
    excel_writer.book = book
    excel_writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    metrics.to_excel(excel_writer, sheet_name=sheet_name)
    try:
        sheet = book['Sheet']
        book.remove(sheet)
        book.save('Portfolio Data.xlsx')
    except KeyError:
        pass
    excel_writer.save()


def formatting_excel(name):
    excel = win32.Dispatch('Excel.Application')
    wkb = excel.Workbooks.Open(r"C:\Users\fabio\PycharmProjects\AlgoTrader\Portfolio Data.xlsx")
    ws = wkb.Worksheets(name)
    ws.Columns.AutoFit()
    wkb.Save()
    excel.Application.Quit()


def web_scraping(tickers):
    r = requests.get('https://www.marketwatch.com/investing/bond/tmubmusd01m?countrycode=bx')
    soup = BeautifulSoup(r.text, 'lxml')
    try:
        bond_list = [entry.text for entry in
                     soup.find_all('span', {'class': 'value'})]
        bond_rate = float(bond_list[-1])
        print("1 month risk-free-rate", str(bond_rate) + str('%'))
    except IndexError:
        print("Failed to fetch 1-Month T-bond Yield! Setting to default value (0.01)")
        bond_rate = 0.01

    for url_stock in tickers:
        quote = {}
        stock_url = 'https://finance.yahoo.com/quote/' + url_stock + '?p=' + url_stock
        r = requests.get(stock_url)
        soup = BeautifulSoup(r.text, 'lxml')
        beta_metric = [entry.text for entry in soup.find_all('span', {'data-reactid': '144'})]
        return_pct = [entry.text for entry in soup.find_all('span', {'data-reactid': '51'})]
        delimiter1 = '('
        delimiter2 = ')'
        formatted_return = str(return_pct[0])
        rt = formatted_return[formatted_return.find(delimiter1) + 1: formatted_return.find(delimiter2)]
        return_string = rt.split("%")[0]
        returns = float(return_string)
        print(url_stock, returns)
        quote['stock'] = url_stock
        quote['beta'] = beta_metric[0]
        quote['returns'] = round(returns, 4)
        quote_data[url_stock] = quote
    # spy
    r = requests.get('https://finance.yahoo.com/quote/SPY?p=SPY')
    soup = BeautifulSoup(r.text, 'lxml')
    spy_returns_pct = [entry.text for entry in soup.find_all('span', {'data-reactid': '51'})]
    delimiter1 = '('
    delimiter2 = ')'
    formatted_return = str(spy_returns_pct[0])
    rt = formatted_return[formatted_return.find(delimiter1) + 1: formatted_return.find(delimiter2)]
    return_string = rt.split("%")[0]
    spy_returns = float(return_string)

    return spy_returns, bond_rate


def purchasing_filter(purchases_df):
    long_purchases_df = purchases_df.loc[(purchases_df['side'] == 'buy') & (purchases_df['cumulative_sum'] > 0)]
    total_long_purchases = round(long_purchases_df['net_trade'].sum(), 2)
    print("Gross cost of long positions:", total_long_purchases)

    short_purchases_df = purchases_df.loc[(purchases_df['side'] == 'buy') & (purchases_df['cumulative_sum'] <= 0)]
    total_short_purchases = round(short_purchases_df['net_trade'].sum(), 2)
    print("Gross cost of short positions:", total_short_purchases)

    long_sales_df = purchases_df.loc[purchases_df['side'] == 'sell']
    total_long_sells = round(long_sales_df['net_trade'].sum(), 2)
    print("Gross profit of long positions:", total_long_sells)

    short_sales_df = purchases_df.loc[purchases_df['side'] == 'sell_short']
    total_short_sells = round(short_sales_df['net_trade'].sum(), 2)
    print("Gross profit of short positions:", total_short_sells)


# minor date functions
def suffix(d):
    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')


def custom_strftime(time_format, t):
    return t.strftime(time_format).replace('{S}', str(t.day) + suffix(t.day))


# needs fix
def alpaca_bootstrapper():
    # Alpaca API Bootstrap
    token_file = open("alpaca_keys.txt")
    keys = token_file.readlines()
    key = keys[0].rstrip('\n')
    sec_key = keys[1].rstrip('\n')
    alpaca_api = trade_api.REST(key, sec_key, URL("https://paper-api.alpaca.markets"), api_version='v2')

    return alpaca_api


def time_initialization():
    fulltimezone = str(dt.datetime.now(dt.timezone.utc).astimezone().tzinfo)
    local_timezone = ''.join([c for c in fulltimezone if c.isupper()])
    proper_date = custom_strftime('%B {S}, %Y', dt.datetime.now())
    print('Today\'s date:', proper_date)
    proper_time = dt.datetime.strftime(dt.datetime.now(), "%I:%M:%S %p")
    print('The time is:', proper_time, local_timezone)

    cstdelta = dt.timedelta(hours=1)
    market_close = (clock.next_close - cstdelta).time()
    mkt_close_time_ampm = market_close.strftime("%#I:%M %p")

    mkt_open_date = custom_strftime('%B {S}, %Y', clock.next_open)
    mkt_open_time = (clock.next_open - cstdelta).time()
    market_open_time_ampm = mkt_open_time.strftime("%#I:%M %p")

    market_closed_boolean = False
    if not clock.is_open:
        print('The stock market is currently closed, but will reopen on:')
        print(mkt_open_date + ' at ' + market_open_time_ampm + ' ' + local_timezone)
        market_closed_boolean = True
    else:
        print('The stock market closes at ' + mkt_close_time_ampm + ' today')

    return market_close, market_closed_boolean


def check_for_market_close():
    if not clock.is_open:
        raise Exception('The market is currently closed')

    tmp_fivemintime = dt.datetime.combine(dt.date(1, 1, 1), market_close)
    fiveminfromclose = (tmp_fivemintime - dt.timedelta(minutes=5)).time()
    if dt.datetime.now().time() > fiveminfromclose:
        raise Exception('The market is closing in 5 minutes, all positions have been closed')


def websocket_boot():
    try:
        socket_th = th.Thread(target=websocket_bootstrap.start_ws)
        socket_th.daemon = True
        socket_th.start()
        print('GUBS')
    except Exception as error:
        print(error)
        websocket_bootstrap.close_ws()


def data_thread_marshaller():
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        stock_quotes = executor.submit(stock_data_bootstrap.quote_data_processor).result()
        technical_indicators = executor.submit(finnhub_tech_bootstrap.tech_indicator).result()

    print(stock_quotes)
    print(technical_indicators)

    for stock in stock_tickers:
        stock_quote_data[stock].append(stock_quotes[stock])
        ti_data[stock].append(technical_indicators[stock])


def initial_analysis():
    pass


def initial_fetch():
    # initial fetches
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        initial_quote_fetch = executor.submit(stock_data_bootstrap.inital_quote_data_fetch).result()
        stock_quotes = executor.submit(stock_data_bootstrap.quote_data_processor).result()
        initial_bond_fetch = executor.submit(bond_bootstrap.onemonthyield).result()
        ti_fetch = executor.submit(finnhub_tech_bootstrap.tech_indicator).result()
    print(initial_bond_fetch)
    print(initial_quote_fetch)
    print(stock_quotes)
    print(ti_fetch)
    bootstrapper = Options(stock_tickers=stock_tickers, initial_data=initial_quote_fetch, quote_data=stock_quotes,
                           rate=initial_bond_fetch)
    options_pricing = bootstrapper.thread_marshaller()
    print(options_pricing)


if __name__ == '__main__':
    notification = ToastNotifier()
    api = alpaca_bootstrapper()
    account = api.get_account()
    clock = api.get_clock()

    account_balance = float(account.buying_power) / 4
    print('Trading account status:', account.status)
    print('Current account balance (without margin) is: $' + str(round(account_balance, 2)))

    market_close, market_closed_boolean = time_initialization()

    manual_override_bool = False
    if input("Manual override? (y/n)") == 'y':
        manual_override_bool = True

    if not market_closed_boolean or manual_override_bool:
        print("Select from one of the following choices:")
        print('Press 1 for Automated Stock Fetch and Trading')
        print('Press 2 for Manual Stock Fetch and Automated Trading')
        print('Press 3 for Portfolio Analysis')
        print('This program is developed solely by Anthony M. Lonsdale')
        print('Contact Information:')
        print('E-mail: alons3253@gmail.com')
        print('Cell: 816-872-7762')

        choice = None
        while True:
            try:
                choice = int(input('Enter: '))
                if choice > 3:
                    raise ValueError
            except ValueError:
                print('Invalid input')
                continue
            else:
                break

        stock_tickers = []
        if choice == 1:
            stock_tickers = APIbootstrap(_api=api).get_tickers()
        if choice == 2:
            print("Input stock tickers separated by a space, the quotes and trades for each stock will be streamed")
            print("When you are done entering tickers, press Enter to show the quotes for each stock in order")
            print("Type 'close' in order to close all current positions")
            stock_tickers = input('Enter Ticker(s): ').upper().split()

            while True:
                try:
                    if stock_tickers == ['CLOSE']:
                        api.cancel_all_orders()
                        api.close_all_positions()
                        stock_tickers = input('Positions have been closed, Enter Ticker(s): ').upper().split()

                    for position, item in enumerate(stock_tickers):
                        try:
                            asset = api.get_asset(item)
                            if not asset.tradable:
                                print(item, 'is not available to trade on Alpaca!')
                                stock_tickers[position] = input('Enter different ticker: ').upper()
                            continue
                        except Exception as e:
                            print(e)
                            print(stock_tickers[position], 'is not a valid ticker!')
                            stock_tickers[position] = input('Enter a different ticker: ').upper()

                    for stock in stock_tickers:
                        try:
                            asset = api.get_asset(stock)
                            if not asset.tradable:
                                raise Exception("Not Tradable")
                        except Exception:
                            raise Exception("Not Tradable")
                    break
                except Exception as stockinputerror:
                    print(stockinputerror)
                    print("There was a problem with the ticker(s) that you entered")
                    continue

        # Start of main program
        if choice == 1 or choice == 2:
            # bootstrappers
            print("Starting Bootstrappers")
            websocket_bootstrap = WebsocketBootStrapper(stock_tickers=stock_tickers)
            stock_data_bootstrap = stockDataEngine(stock_tickers=stock_tickers)
            finnhub_tech_bootstrap = technicalIndicators(stock_tickers=stock_tickers)
            bond_bootstrap = riskfreerate()

            while True:
                trade_data = {}
                stock_quote_data = {}
                ti_data = {}
                for stock in stock_tickers:
                    trade_data[stock] = []
                    stock_quote_data[stock] = []
                    ti_data[stock] = []
                errormessage_market_close = 'The market is currently closed'
                errormessage_5min_to_close = 'The market is closing in 5 minutes, be warned that any new positions ' \
                                             'may be held until the next trading day'
                errormessage_trade_fetch = 'No trades gathered'
                cutoff_bool = False
                #######################################################################################################
                print("Starting Initial Fetch, this will take several minutes")
                initial_fetch()
                websocket_boot()
                # initial_analysis()
                while True:
                    data_thread_marshaller()
                    trade_data = websocket_bootstrap.return_data()
                    print(trade_data)
                    time.sleep(10)

                    # we need to run this at the start of the day in order to see what opportunities there are
                    # data_thread_marshaller()

    # START OF PORTFOLIO ANALYSIS
    if not os.path.isfile(r"/Miscellaneous Files/Misc/Portfolio Data.xlsx"):
        wb = openpyxl.Workbook()
        wb.save('Portfolio Data.xlsx')

    pd.options.mode.chained_assignment = None
    days = 0
    activities_df = None
    open_tickers = None
    open_position_catalog = None

    while True:
        try:
            spec_date = dt.datetime.today() - dt.timedelta(days=days)
            date = spec_date.strftime('%Y-%m-%d')
            print('Attempting to analyze portfolio on {}'.format(date))
            activities = api.get_activities(activity_types='FILL', date=date)
            activities_df = pd.DataFrame([activity._raw for activity in activities])
            if not len(activities_df) > 10:
                # print(activities_df)
                time.sleep(0.1)
                raise Exception("Not enough trades for analysis")

            print("Analyzing portfolio activities on {}".format(date))
            activities_df = pd.DataFrame([activity._raw for activity in activities])
            activities_df = activities_df.iloc[::-1]
            activities_df[['price', 'qty']] = activities_df[['price', 'qty']].apply(pd.to_numeric)
            activities_df['net_qty'] = np.where(activities_df.side == 'buy', activities_df.qty, -activities_df.qty)
            activities_df['net_trade'] = -activities_df.net_qty * activities_df.price
            activities_df['cumulative_sum'] = activities_df.groupby('symbol')['net_qty'].apply(lambda g: g.cumsum())
            activities_df.to_excel("Portfolio Activities, {}.xlsx".format(date))
            stock_tickers = list(activities_df.symbol.unique())
            print(stock_tickers)

            # check if there were any open positions on the previous day
            try:
                prev_day_spec_date = dt.datetime.today() - dt.timedelta(days=(days+1))
                prev_day_date = prev_day_spec_date.strftime('%Y-%m-%d')
                prev_day_activities = api.get_activities(activity_types='FILL', date=prev_day_date)
                prev_days_activities_df = pd.DataFrame([activity._raw for activity in prev_day_activities])
                prev_days_activities_df = prev_days_activities_df.iloc[::-1]
                prev_days_activities_df[['price', 'qty']] = \
                    prev_days_activities_df[['price', 'qty']].apply(pd.to_numeric)
                prev_days_activities_df['net_qty'] = np.where(prev_days_activities_df.side == 'buy',
                                                              prev_days_activities_df.qty, -prev_days_activities_df.qty)
                prev_days_activities_df['net_trade'] = -prev_days_activities_df.net_qty * prev_days_activities_df.price
                prev_days_activities_df['cumulative_sum'] = prev_days_activities_df.groupby('symbol')['net_qty'].apply(
                                                                                                lambda h: h.cumsum())
                prev_days_activities_df.to_excel("Portfolio Activities, {}.xlsx".format(prev_day_date))

                nonzero_trades = prev_days_activities_df.groupby('symbol').filter(lambda trade: sum(trade.net_qty) != 0)
                open_position_catalog = {}
                open_tickers = nonzero_trades.symbol.unique()
                print(open_tickers)

                nonzero_trades = nonzero_trades.iloc[::-1]
                for stock in open_tickers:
                    boolean_rectified_open_position = False
                    open_position_catalog[stock] = []
                    open_position_qty = nonzero_trades.iloc[0]['cumulative_sum']
                    for index, row in nonzero_trades.copy().iterrows():
                        if boolean_rectified_open_position:
                            break
                        if row.symbol == stock:
                            if row.net_qty == open_position_qty:
                                open_position_catalog[stock].append(row)
                                nonzero_trades = nonzero_trades[nonzero_trades['symbol'] != stock]
                                boolean_rectified_open_position = True
                            else:
                                open_position_qty -= row.net_qty
                                open_position_catalog[stock].append(row)

                for stock in open_tickers:
                    open_position_catalog[stock] = reversed(open_position_catalog[stock])
                    activities_df = pd.concat([pd.DataFrame(open_position_catalog[stock]), activities_df],
                                              ignore_index=True)
            except Exception as e:
                print("Based on the lack of previous days trades, there is probably not an open position")
            break
        except Exception as e:
            if str(e) == str('Not enough trades for analysis'):
                days += 1
            else:
                print('Program ran into the following error while trying to analyze portfolio data:')
                print(e)
                raise sys.exit(0)

    ###################################################################################################################
    # Total Net Profit for Long and Short Trades
    purchasing_filter(activities_df)
    trade_book = {}
    short_trade_book = {}
    short_order_time_held = {}
    long_order_time_held = {}
    for stock in stock_tickers:
        trade_book[stock] = []
        short_trade_book[stock] = []
        short_order_time_held[stock] = []
        long_order_time_held[stock] = []
        trades_list = []
        for index, row in activities_df.iterrows():
            grouped_trades = {}
            if row['symbol'] == stock:
                grouped_trades.update(row)
                trades_list.append(grouped_trades)

        grouped_trades_df = pd.DataFrame(trades_list)
        excel_title = str(stock) + str(' Trades for ') + str(date) + str('.xlsx')
        grouped_trades_df['cumulative_sum'] = grouped_trades_df.groupby('symbol')['net_qty'].apply(lambda h: h.cumsum())
        # grouped_trades_df.to_excel(excel_title)

        # here is where the trades will be settled
        rows_to_drop = []
        length_of_df = grouped_trades_df.index
        for index, row in grouped_trades_df.copy().iterrows():
            if grouped_trades_df['type'][index] == 'partial_fill':
                # noinspection PyTypeChecker
                for i in range((index+1), (len(length_of_df) - 1)):
                    if grouped_trades_df['side'][index] == grouped_trades_df['side'][i]:
                        grouped_trades_df['qty'][i] += grouped_trades_df['qty'][index]
                        grouped_trades_df['net_qty'][i] += grouped_trades_df['net_qty'][index]
                        grouped_trades_df['net_trade'][i] += grouped_trades_df['net_trade'][index]
                        rows_to_drop.append(index)
                        break
        for rowtodrop in rows_to_drop:
            grouped_trades_df = grouped_trades_df.drop(rowtodrop)
        # grouped_trades_df.to_excel('Settled {} Trades, {}.xlsx'.format(stock, date))
        same_side_orders = []
        txn_time1 = None
        net_trade1 = None
        side1 = None
        qty1 = None
        reset_flag = True
        for index, row in grouped_trades_df.copy().iterrows():
            if reset_flag:
                txn_time1 = dt.datetime.strptime(grouped_trades_df['transaction_time'][index], "%Y-%m-%dT%H:%M:%S.%fZ")
                net_trade1 = grouped_trades_df['net_trade'][index]
                side1 = grouped_trades_df['side'][index]
                qty1 = grouped_trades_df['qty'][index]
                same_side_orders.append([txn_time1, net_trade1, qty1, side1])
                reset_flag = False
                continue

            txn_time2 = dt.datetime.strptime(grouped_trades_df['transaction_time'][index], "%Y-%m-%dT%H:%M:%S.%fZ")
            net_trade2 = grouped_trades_df['net_trade'][index]
            side2 = grouped_trades_df['side'][index]
            qty2 = grouped_trades_df['qty'][index]

            if side2 == side1:
                same_side_orders.append([txn_time2, net_trade2, qty2, side2])
            elif side1 == 'sell_short' and side2 == 'buy':
                if qty2 > qty1:
                    for i in range(len(same_side_orders)):
                        profitloss = round(same_side_orders[0][1] + ((net_trade2 / qty2) * same_side_orders[0][2]), 2)
                        short_trade_book[stock].append(profitloss)
                        time_held = (txn_time2 - same_side_orders[0][0]).total_seconds()
                        short_order_time_held[stock].append((time_held, same_side_orders[0][2]))
                        same_side_orders.pop(0)
                else:
                    profitloss = round(same_side_orders[0][1] + net_trade2, 2)
                    short_trade_book[stock].append(profitloss)
                    time_held = (txn_time2 - txn_time1).total_seconds()
                    short_order_time_held[stock].append((time_held, qty2))
                    same_side_orders.pop(0)
            elif side1 == 'buy' and side2 == 'sell':
                if qty2 > qty1:
                    for i in range(len(same_side_orders)):
                        profitloss = round(same_side_orders[0][1] + ((net_trade2 / qty2) * same_side_orders[0][2]), 2)
                        short_trade_book[stock].append(profitloss)
                        time_held = (txn_time2 - same_side_orders[0][0]).total_seconds()
                        long_order_time_held[stock].append((time_held, same_side_orders[0][2]))
                        same_side_orders.pop(0)
                else:
                    profitloss = round(same_side_orders[0][1] + net_trade2, 2)
                    trade_book[stock].append(profitloss)
                    time_held = (txn_time2 - txn_time1).total_seconds()
                    long_order_time_held[stock].append((time_held, qty2))
                    same_side_orders.pop(0)
            if len(same_side_orders) == 0:
                reset_flag = True

    print(trade_book)
    print(short_trade_book)
    print(long_order_time_held)
    print(short_order_time_held)

    total_profit = 0
    profit_per_symbol = {}
    for stock in trade_book:
        profit_per_symbol[stock] = 0
        for element in trade_book[stock]:
            total_profit += float(element)
            profit_per_symbol[stock] += float(element)
        for element in short_trade_book[stock]:
            total_profit += float(element)
            profit_per_symbol[stock] += float(element)
    print(round(total_profit, 2))
    print("Note that there may be a slight discrepancy in calculated prices vs what alpaca's interface shows, \n"
          "This is simply due to the fact this calculation concerns CLOSED trades, and doesnt consider the \n"
          "changing value of stock(s) held")
    ####################################################################################################################
    short_hold_time = 0
    longtime = 0
    longquantity = 0
    long_length = 0
    shorttime = 0
    shortquantity = 0
    short_length = 0

    for stock in stock_tickers:
        for i in range(len(long_order_time_held[stock])):
            longtime += long_order_time_held[stock][i][0]
            longquantity += long_order_time_held[stock][i][1]
            long_length += 1
        for i in range(len(short_order_time_held[stock])):
            shorttime += short_order_time_held[stock][i][0]
            shortquantity += short_order_time_held[stock][i][1]
            short_length += 1

    avg_long_stock_hold_time = round(longtime / longquantity, 2)
    avg_short_stock_hold_time = round(shorttime / shortquantity, 2)
    avg_long_trade_hold_time = round(longtime / long_length, 2)
    avg_short_trade_hold_time = round(shorttime / short_length, 2)
    print("Average stock held for:", round(avg_long_stock_hold_time, 2), 'seconds')
    print("Average short stock held for:", round(avg_short_stock_hold_time, 2), 'seconds')

    avg_total_trade_length = time.strftime("%#M:%S", time.gmtime((avg_short_trade_hold_time +
                                                                  avg_long_trade_hold_time)))
    avg_short_trade_length = time.strftime("%#M:%S", time.gmtime(avg_short_trade_hold_time))
    avg_long_trade_length = time.strftime("%#M:%S", time.gmtime(avg_long_trade_hold_time))

    print("Average long trade held for:", avg_long_trade_length)
    print("Average short trade held for:", avg_short_trade_length)
    ##################################################################
    total_gross_profit = 0
    total_gross_loss = 0
    short_gross_profit = 0
    short_gross_loss = 0
    net_short_profit = 0
    total_short_trades = 0
    short_winning_trades = 0
    short_even_trades = 0
    short_losing_trades = 0

    for stock in short_trade_book:
        for i in range(len(short_trade_book[stock])):
            if short_trade_book[stock][i] > 0:
                short_winning_trades += 1
                short_gross_profit += short_trade_book[stock][i]
                total_gross_profit += short_trade_book[stock][i]
            elif short_trade_book[stock][i] < 0:
                short_losing_trades += 1
                short_gross_loss += short_trade_book[stock][i]
                total_gross_loss += short_trade_book[stock][i]
            else:
                short_even_trades += 1
            total_short_trades += 1
            net_short_profit += short_trade_book[stock][i]

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
    for stock in trade_book:
        for i in range(len(trade_book[stock])):
            if trade_book[stock][i] > 0:
                long_winning_trades += 1
                long_gross_profit += trade_book[stock][i]
                total_gross_profit += trade_book[stock][i]
            elif trade_book[stock][i] < 0:
                long_losing_trades += 1
                long_gross_loss += trade_book[stock][i]
                total_gross_loss += trade_book[stock][i]
            else:
                long_even_trades += 1
            total_long_trades += 1
            net_long_profit += trade_book[stock][i]

    net_long_profit = round(net_long_profit, 2)
    print("\nLong-side net profit:", net_long_profit)
    print("Long-side profitable trades:", long_winning_trades)
    print("Long-side even trades:", long_even_trades)
    print("Long-side losing trades:", long_losing_trades)
    print("Total long-side trades", total_long_trades)

    avg_winning_trade = round((total_gross_profit / (long_winning_trades + short_winning_trades)), 2)
    avg_losing_trade = round((total_gross_loss / (total_long_trades + short_losing_trades)), 2)
    avg_long_winning_trade = round(long_gross_profit / long_winning_trades, 2)
    avg_long_losing_trade = round(long_gross_loss / long_losing_trades, 2)
    avg_short_winning_trade = round(short_gross_profit / short_winning_trades, 2)
    avg_short_losing_trade = round(short_gross_loss / short_losing_trades, 2)

    todays_profit_and_loss = round(total_gross_profit + total_gross_loss, 2)
    total_gross_profit = round(total_gross_profit, 2)
    total_gross_loss = round(total_gross_loss, 2)

    print("\nProfit Metrics:")
    print("Gross Profit:", total_gross_profit)
    print("Average Winning Trade:", avg_winning_trade)
    print("Gross Loss:", total_gross_loss)
    print("Average Losing Trade:", avg_losing_trade)
    print("Total Net Profit:", todays_profit_and_loss)

    #############################################################################
    pd.options.display.float_format = '{:.0f}'.format
    quote_data = {}
    for stock in stock_tickers:
        quote_data[stock] = {}
    #########################################################################################
    # for quick debugging
    spyreturn, riskfreerate = web_scraping(stock_tickers)
    spyreturn = '{:.4f}'.format(spyreturn)
    spyreturn = float(spyreturn)
    print(quote_data)
    print(spyreturn)
    #############################################################################
    stock_metrics = [['' for m in range(1)] for i in range(len(stock_tickers) * 3)]
    spdr_string = str(spyreturn) + str('%')
    spdr_list = ["Daily return of $SPY", spdr_string]

    stock_index = 0
    for stock in stock_tickers:
        # the average max holdings of each stock is limited at 10% of the portfolio
        trade_size_relative_to_portfolio = 0.1
        beta = trade_size_relative_to_portfolio * float(quote_data[stock]['beta'])
        buying_power = float(account.buying_power) / 4
        stock_profit_pct = round((profit_per_symbol[stock] / buying_power) * 100, 4)
        market_returns_pct = quote_data[stock]['returns']
        # divide the 1 month risk free rate by 30 to approximate the rate of bond return for 1 day
        alpha = round((stock_profit_pct - (riskfreerate / 30)) - (beta * (spyreturn - (riskfreerate / 30))), 4)

        list1 = ["Performance of {}:".format(stock), str(market_returns_pct) + str('%')]
        list2 = ["Performance of {} relative to $SPY:".format(stock), str(round(market_returns_pct - spyreturn, 2)) +
                 str('%')]
        list3 = ["\"Alpha\" trading performance of {}:".format(stock), str(alpha) + str('%')]

        stock_metrics[stock_index] = list1
        stock_metrics[stock_index + 1] = list2
        stock_metrics[stock_index + 2] = list3

        print(list1)
        print(list2)
        print(list3)
        stock_index += 3

    # if the total gross profit of the stock is not positive then the gross loss must be flipped in order to generate a
    # non negative percentage for the profit factor of the portfolio
    if total_gross_profit > -total_gross_loss:
        total_profit_factor = round((total_gross_profit / -total_gross_loss), 2)
    else:
        total_profit_factor = round((total_gross_profit / total_gross_loss), 2)

    if long_gross_profit > -long_gross_loss:
        long_profit_factor = round((long_gross_profit / -long_gross_loss), 2)
    else:
        long_profit_factor = round((long_gross_profit / long_gross_loss), 2)

    if short_gross_profit > -short_gross_loss:
        short_profit_factor = round((short_gross_profit / -short_gross_loss), 2)
    else:
        short_profit_factor = round((short_gross_profit / short_gross_loss), 2)

    total_percent_profitable = round(((long_winning_trades + short_winning_trades) / (total_long_trades +
                                                                                      total_short_trades)) * 100, 2)
    long_percent_profitable = round((long_winning_trades / total_long_trades) * 100, 2)
    short_percent_profitable = round((short_winning_trades / total_short_trades) * 100, 2)
    no_of_stock_metrics = len(stock_metrics)

    # this is the 2d list used to convert into a pandas dataframe for easy transcription onto an excel document
    data = [['Profit Metrics', '', '', ''],
            ['Total Net Profit:', todays_profit_and_loss, net_long_profit, net_short_profit],
            ['Gross Profit:', total_gross_profit, long_gross_profit, short_gross_profit],
            ['Gross Loss:', total_gross_loss, long_gross_loss, short_gross_loss],
            ['Profit Factor:', total_profit_factor, long_profit_factor, short_profit_factor],
            ['', '', '', ''],
            ['Trade Metrics', '', '', ''],
            ['Total Number of Trades:', int(total_long_trades + total_short_trades), total_long_trades,
             total_short_trades],
            ['Percent Profitable:', str(total_percent_profitable) + str("%"), str(long_percent_profitable) + str('%'),
             str(short_percent_profitable) + str('%')],
            ['Average Stock Held Time (Seconds):', avg_total_trade_length, avg_long_trade_length,
             avg_short_trade_length],
            ['Winning Trades:', long_winning_trades + short_winning_trades, long_winning_trades, short_winning_trades],
            ['Average Winning Trade:', avg_winning_trade, avg_long_winning_trade, avg_short_winning_trade],
            ['Losing Trades:', long_losing_trades + short_losing_trades, long_losing_trades, short_losing_trades],
            ['Average Losing Trade:', avg_losing_trade, avg_long_losing_trade, avg_short_losing_trade],
            ['Even Trades', long_even_trades + short_even_trades, long_even_trades, short_even_trades],
            ['', '', '', ''],
            ['Stock Metrics', '', '', ''],
            spdr_list] + stock_metrics

    # if i want to add further rows in the future, simply do
    # data + 2d list

    portfolio_metrics = DataFrame(data, columns=['Performance Summary', 'All Trades', 'Long Trades', 'Short Trades'])
    sheet_name = str('Performance on ') + str(date)
    data_to_excel(portfolio_metrics)
    formatting_excel(sheet_name)
