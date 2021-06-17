# updated to full functionality

import pandas as pd
from win10toast import ToastNotifier
import alpaca_trade_api as trade_api
from alpaca_trade_api.stream import URL
import openpyxl
import os
import concurrent.futures
import datetime as dt
import time
import threading as th

from ALGO.stock_init_fetch_module import APIbootstrap
from ALGO.websocket_core_module import WebsocketBootStrapper
from ALGO.stock_data_module import stockDataEngine
from ALGO.technical_indicators_core import technicalIndicators
from ALGO.bond_yield_fetch import onemonthyield
from ALGO.options_module import Options
from ALGO.portfolio_analysis_module import portfolioAnalysis


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
            bond_bootstrap = onemonthyield()

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
    if not os.path.isfile(r"Portfolio Data.xlsx"):
        wb = openpyxl.Workbook()
        wb.save('Portfolio Data.xlsx')

    portfolio_bootstrap = portfolioAnalysis(api=api)
    portfolio_bootstrap.main()
