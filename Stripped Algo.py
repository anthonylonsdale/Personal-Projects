import requests
import websocket
import json
import threading as th
import alpaca_trade_api as trade_api
import pandas as pd
import time
import datetime as dt
import openpyxl
import os
import clr


def on_message(ws, message):
    if message == '{"type":"ping"}':
        return
    data = json.loads(message)
    stock_fundamentals = data['data'][0]
    time_integer = stock_fundamentals['t']
    timestamp = dt.datetime.fromtimestamp(time_integer / 1e3)
    timestamp = str("{}.{:03d}".format(timestamp.strftime('%Y-%m-%d %H:%M:%S'), timestamp.microsecond // 1000))
    stock_fundamentals['t'] = timestamp
    stock = stock_fundamentals['s']
    stock_fundamentals['time'] = stock_fundamentals.pop('t')
    stock_fundamentals['price'] = stock_fundamentals.pop('p')
    stock_fundamentals['stock'] = stock_fundamentals.pop('s')
    stock_fundamentals['volume'] = stock_fundamentals.pop('v')
    print(stock_fundamentals)
    trade_data[stock].append(stock_fundamentals)


def on_error(ws, error):
    print(error)


def on_close(ws):
    print("### closed ###")


def on_open(ws):
    for stock_ticker in stock_tickers:
        custom_call = str('{"type":"subscribe","symbol":"') + stock_ticker + str('"}')
        print(custom_call)
        ws.send(custom_call)


def stock_data_engine():
    clr.AddReference(r"C:\Users\fabio\source\repos\Webscraper Class Library\Webscraper Class Library\bin\Debug\Web"
                     r"scraper Class Library.dll")
    import CSharpwebscraper
    scraper = CSharpwebscraper.Webscraper()
    stock_info = scraper.Scraper(stock_tickers)
    print(stock_info)
    quote = {}
    for i in range(len(stock_info)):
        if (i % 6) == 0:
            quote['current price'] = float(stock_info[i].replace(",", ""))
        if (i % 6) == 1:
            quote['open price'] = float(stock_info[i].replace(",", ""))
        if (i % 6) == 2:
            quote['previous close'] = float(stock_info[i].replace(",", ""))
        if (i % 6) == 3:
            quote['indicator'] = str(stock_info[i])
        if (i % 6) == 4:
            delimiter1 = '('
            delimiter2 = ')'
            div = str(stock_info[i])
            dividend = div[div.find(delimiter1)+1: div.find(delimiter2)]
            if dividend == 'N/A':
                dividend = 0
            else:
                div_string = dividend.split("%")[0]
                dividend = float(div_string) / 100
            quote['dividend'] = dividend
        if (i % 6) == 5:
            stock = str(stock_info[i])
            quote['stock'] = stock
            quote['time'] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            quote_data[stock].append(quote)
            quote = {}
            df_quote = pd.DataFrame(quote_data[stock])
            df_quote.set_index('time', inplace=True)
            print(df_quote)


def tech_indicators():
    # attempt to get the most accurate data possible from the API, retry with wider timescales if unsuccessful
    resolution = ['1', '5', '15', '30', '60', 'D', 'W', 'M']
    for stock in stock_tickers:
        i = 0
        while True:
            try:
                timestamp_tech = time.strftime("%Y-%m-%d %H:%M:%S")
                tech_url = 'https://finnhub.io/api/v1/scan/technical-indicator?symbol=' + stock + \
                           '&resolution=' + resolution[i] + '&token=' + websocket_token
                r = requests.get(tech_url)
                ti = r.json()
                technical = ti['technicalAnalysis']['count']
                technical['signal'] = ti['technicalAnalysis']['signal']
                technical['adx'] = ti['trend']['adx']
                technical['trending'] = ti['trend']['trending']
                technical['time'] = timestamp_tech
                ti_data[stock].append(technical)
                df_tech = pd.DataFrame(ti_data[stock])
                df_tech.set_index('signal', inplace=True)
                print(df_tech)
            except KeyError:
                if i == 7:
                    break
                i += 1
            break


def main_data_engine():
    """
    The purpose of this function is to ensure that all of our data collection APIs and functions dispatch at the same
    time. Theoretically, as long as these functions finish at relatively the same time, we can include it in a thread,
    potentially having dozens of sources to pull data from (although this would be a massive drain on the computer's
    resources, the chrome web scraper rockets the usage of memory from ~20% to 60-70% when it is called). This is a
    dynamic system so we can change what interval we take in order to gather all the relevant data. Unfortunately there
    must be a balancing act, 10 seconds of data collection would mean a very accurate monitor and hold on the realtime
    stock price, potentially significantly reducing losses due to being able to monitor trades many times a minute, but
    this comes at a cost of only implementing data collection functions that are quick enough to run and finish within
    the short time frame. The opposite is true if the interval is stretched out closer to a minute for example.
    """
    try:
        t1 = th.Thread(target=socket.run_forever)
        t1.daemon = True
        t1.start()
        t2 = th.Thread(target=stock_data_engine)
        t2.daemon = True
        t2.start()
        t3 = th.Thread(target=tech_indicators)
        t3.daemon = True
        t3.start()
        time.sleep(20)
        socket.keep_running = False
        socket.close()
        t1.join()
    except Exception as error:
        print(error)
        socket.close()


def ticker_operations():
    """
    this is the best system I can come up with. Have a dynamic system of indicators being gathered and have each one
    "vote" on an outcome, either bullish or bearish. Later on in the program we will use this to make our final decision
    as to buy or not.
    The Finnhub API gathers an aggregate of 17 different indicators, the Yahoo API uses a grouping of indicators as well
    the goal is to extract the number of indicators from each source
    """
    for element in stock_tickers:
        timestamp = dt.datetime.strptime(quote_data[element][-1]['time'][11::], '%H:%M:%S').time()
        indicator = quote_data[element][-1]['indicator']
        if len(ti_data) > 0:
            buy_votes = int(ti_data[element][-1]['buy'])
            sell_votes = int(ti_data[element][-1]['sell'])
            neutral_votes = int(ti_data[element][-1]['neutral'])
            indicator_votes[element]['Bullish Votes'] += buy_votes
            indicator_votes[element]['Bearish Votes'] += sell_votes
            indicator_votes[element]['Neutral Votes'] += neutral_votes

        if indicator == 'Bullish':
            indicator_votes[element]['Bullish Votes'] += 1
        if indicator == 'Bearish':
            indicator_votes[element]['Bearish Votes'] += 1

        if indicator_votes[element]['Bullish Votes'] > indicator_votes[element]['Bearish Votes'] and \
                indicator_votes[element]['Bullish Votes'] > indicator_votes[element]['Neutral Votes']:
            stock_buylist[element].append('Very Bullish at: ' + str(timestamp))
        elif indicator_votes[element]['Bullish Votes'] > indicator_votes[element]['Bearish Votes']:
            stock_buylist[element].append('Bullish at: ' + str(timestamp))

        if indicator_votes[element]['Bearish Votes'] > indicator_votes[element]['Bullish Votes'] and \
                indicator_votes[element]['Bearish Votes'] > indicator_votes[element]['Neutral Votes']:
            stock_shortlist[element].append('Very Bearish at: ' + str(timestamp))
        elif indicator_votes[element]['Bearish Votes'] > indicator_votes[element]['Bullish Votes']:
            stock_shortlist[element].append('Bearish at: ' + str(timestamp))

    print('Stocks of interest:', stock_tickers)
    print('Buy Side Stocklist:', stock_buylist)
    print('Sell Side Stocklist:', stock_shortlist)
    print('------------------------------------------------------------------------')


def volume_operations():
    """
    The purpose of this function is twofold, organize all of the trades we are gathering from the websocket into 4
    separate intervals in order to determine if there is significant volatility, as well as to use the last 25 trades
    in order to determine what price the stock is currently trading at (over the course of the 1-2 seconds of analysis
    that this program needs, the stock price is liable to change, albeit slightly, making this necessary)
    """
    for element in stock_tickers:
        volume_past_30sec = 0
        volume_past_min = 0
        volume_past_2min = 0
        volume_past_5min = 0
        stock_price = 0
        stock_list_length[element] = 0
        length = []
        stock_prices[element] = []
        for position, item in enumerate(trade_data[element]):
            if position >= int(len(trade_data[element]) - 25):
                stock_price += item['price']
                length.append(item)
                stock_list_length[element] = int(len(length))
            if dt.datetime.strptime(item['time'], "%Y-%m-%d %H:%M:%S.%f") > dt.datetime.now() - dt.timedelta(
                    seconds=30):
                volume_past_30sec += int(item['volume'])
            if dt.datetime.strptime(item['time'], "%Y-%m-%d %H:%M:%S.%f") > dt.datetime.now() - dt.timedelta(
                    seconds=60):
                volume_past_min += int(item['volume'])
            if dt.datetime.strptime(item['time'], "%Y-%m-%d %H:%M:%S.%f") > dt.datetime.now() - dt.timedelta(
                    seconds=120):
                volume_past_2min += int(item['volume'])
            if dt.datetime.strptime(item['time'], "%Y-%m-%d %H:%M:%S.%f") > dt.datetime.now() - dt.timedelta(
                    seconds=300):
                volume_past_5min += int(item['volume'])
        ##############################################################################
        stock_prices[element] = float("{:.2f}".format(stock_price / stock_list_length[element]))
        volume_terms[element] = volume_past_30sec, volume_past_min, volume_past_2min, volume_past_5min
        # this establishes volumes for time intervals, such that if say the thirty second volume exceeds the minute
        # volume, this is obviously a spike in volume and represents volatility which can be profitable
        # obviously we can change the time interval and increase or decrease them as needed
    print('volume by stock ordered 30sec, 1min, 2min and 5min:', volume_terms)
    print('stock prices:', stock_prices)


# might need rework and additional analysis
def analysis_operations():
    # this block is only to see if the stock has had an increase or decrease in short term price respectively
    # if the following conditions are met, then this represents a good trade opportunity
    # this portion works
    for stock in stock_buylist:
        for position, item in enumerate(quote_data[stock]):
            if dt.datetime.strptime(quote_data[stock][position]['time'], "%Y-%m-%d %H:%M:%S") > \
                    (dt.datetime.now() - dt.timedelta(minutes=5)):
                if position == (len(quote_data[stock]) - 1) and quote_data[stock][position]['current price'] < \
                        stock_prices[stock]:
                    stock_price_movement[stock] = 'short-term increase in price'
    for stock in stock_shortlist:
        for position, item in enumerate(quote_data[stock]):
            if dt.datetime.strptime(quote_data[stock][position]['time'], "%Y-%m-%d %H:%M:%S") > \
                    (dt.datetime.now() - dt.timedelta(minutes=5)):
                # if current price is lower than quote price
                if position == (len(quote_data[stock]) - 1) and quote_data[stock][position]['current price'] > \
                        stock_prices[stock]:
                    stock_price_movement[stock] = 'short-term decrease in price'
    print(stock_price_movement)

    for stock in stock_price_movement:
        if 'increase' in stock_price_movement[stock]:
            if len(stock_buylist[stock]) > 2:
                if quote_data[stock][-1]['current price'] > quote_data[stock][-2]['current price'] > \
                        quote_data[stock][-3]['current price']:
                    if 'Very Bullish' in stock_buylist[stock][-1] and 'Very Bullish' in stock_buylist[stock][-2]:
                        strongbuy[stock] = stock
                elif quote_data[stock][-1]['current price'] > quote_data[stock][-2]['current price']:
                    if 'Bullish' in stock_buylist[stock][-1] and 'Bullish' in stock_buylist[stock][-2]:
                        buy[stock] = stock
                else:
                    weakbuy[stock] = stock
        if 'decrease' in stock_price_movement[stock]:
            if len(stock_shortlist[stock]) > 2:
                if quote_data[stock][-1]['current price'] < quote_data[stock][-2]['current price'] < \
                        quote_data[stock][-3]['current price']:
                    if 'Very Bearish' in stock_shortlist[stock][-1] and 'Very Bearish' in stock:
                        strongsell[stock] = stock
                elif quote_data[stock][-1]['current price'] < quote_data[stock][-2]['current price']:
                    if 'Bearish' in stock_shortlist[stock][-1] and 'Bearish' in stock_shortlist[stock][-2]:
                        sell[stock] = stock
                else:
                    weaksell[stock] = stock

    if len(strongbuy) > 0:
        print('Stock Strong Buy List:', strongbuy)
    if len(buy) > 0:
        print('Stock Buy List:', buy)
    if len(weakbuy) > 0:
        print('Stock Weak Buy List:', weakbuy)
    if len(strongsell) > 0:
        print('Stock Strong Sell List:', strongsell)
    if len(sell) > 0:
        print('Stock Sell List:', sell)
    if len(weaksell) > 0:
        print('Stock Weak Sell List:', weaksell)


def trade_execution_operations():
    try:
        if account_balance < 0.50 * float(account.equity):
            return
        # long trades
        for element in strongbuy:
            price = stock_prices[element]
            account_percentage = (account_balance * 0.04) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = 1.01 * price
            stop_loss = 0.9925 * price
            limit_price2 = .9910 * price
            api.submit_order(symbol=element, qty=round_lot, side='buy', type='market', time_in_force='gtc',
                             order_class='bracket', take_profit={'limit_price': limit_price},
                             stop_loss={'stop_price': stop_loss, 'limit_price': limit_price2})
            strongbuy[element] = []
        for element in buy:
            price = stock_prices[element]
            account_percentage = (account_balance * 0.03) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = 1.008 * price
            stop_loss = 0.9930 * price
            limit_price2 = 0.9920 * price
            api.submit_order(symbol=element, qty=round_lot, side='buy', type='market', time_in_force='gtc',
                             order_class='bracket', take_profit={'limit_price': limit_price},
                             stop_loss={'stop_price': stop_loss, 'limit_price': limit_price2})
            buy[element] = []
        for element in weakbuy:
            price = stock_prices[element]
            account_percentage = (account_balance * 0.025) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = 1.006 * price
            stop_loss = 0.9940 * price
            limit_price2 = 0.9930 * price
            api.submit_order(symbol=element, qty=round_lot, side='buy', type='market', time_in_force='gtc',
                             order_class='bracket', take_profit={'limit_price': limit_price},
                             stop_loss={'stop_price': stop_loss, 'limit_price': limit_price2})
            buy[element] = []
        # short trades
        for element in strongsell:
            price = stock_prices[element]
            account_percentage = (account_balance * 0.04) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = .99 * price
            stop_loss = 1.075 * price
            limit_price2 = 1.090 * price
            api.submit_order(symbol=element, qty=round_lot, side='sell', type='market', time_in_force='gtc',
                             order_class='bracket', take_profit={'limit_price': limit_price},
                             stop_loss={'stop_price': stop_loss, 'limit_price': limit_price2})
            strongsell[element] = []
        for element in sell:
            price = stock_prices[element]
            account_percentage = (account_balance * 0.03) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = .992 * price
            stop_loss = 1.070 * price
            limit_price2 = 1.080 * price
            api.submit_order(symbol=element, qty=round_lot, side='sell', type='market', time_in_force='gtc',
                             order_class='bracket', take_profit={'limit_price': limit_price},
                             stop_loss={'stop_price': stop_loss, 'limit_price': limit_price2})
            sell[element] = []
        for element in weaksell:
            price = stock_prices[element]
            account_percentage = (account_balance * 0.025) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = .994 * price
            stop_loss = 1.060 * price
            limit_price2 = 1.070 * price
            api.submit_order(symbol=element, qty=round_lot, side='sell', type='market', time_in_force='gtc',
                             order_class='bracket', take_profit={'limit_price': limit_price},
                             stop_loss={'stop_price': stop_loss, 'limit_price': limit_price2})
            weaksell[element] = []
    except Exception as error:
        print(error)
        api.cancel_all_orders()
        print('There was an error with the trade execution, all orders have been suspended')


def check_trades():
    # if no trades are gathered, then the program needs to go back to the web socket and run again till we get trades
    if len(trade_data) == 0:
        print('No trades were gathered')
        return False
    return True


def cleanup():
    # get rid of all trades from before 5 minutes ago
    if (end - start) > 300:
        for element in stock_tickers:
            for position, item in enumerate(trade_data[element]):
                if dt.datetime.strptime(item['time'], "%Y-%m-%d %H:%M:%S.%f") < \
                        dt.datetime.now() - dt.timedelta(seconds=300):
                    trade_data[element].remove(item)
            for position, item in enumerate(quote_data[element]):
                if dt.datetime.strptime(item['time'], "%Y-%m-%d %H:%M:%S.%f") < \
                        dt.datetime.now() - dt.timedelta(seconds=300):
                    quote_data[element].remove(item)
            for position, item in enumerate(ti_data[element]):
                if dt.datetime.strptime(item['time'], "%Y-%m-%d %H:%M:%S.%f") < \
                        dt.datetime.now() - dt.timedelta(seconds=300):
                    ti_data[element].remove(item)


def check():
    close = dt.datetime.strptime(market_close, '%Y-%m-%d %H:%M:%S.%f')
    if dt.datetime.now() > (close - dt.timedelta(minutes=70)):
        api.close_all_positions()
        api.cancel_all_orders()
        raise Exception('The market is closing in 10 minutes, all positions have been closed')


def check_excel_file():
    wb = openpyxl.Workbook()
    wb.save('Options Data.xlsx')


if __name__ == '__main__':
    # we want to make sure a new excel file is used each time the program opens to reduce issues of corrupted files
    cwd = os.getcwd() + r'\Options Data.xlsx'
    if os.path.isfile(r"{}".format(cwd)):
        os.remove("Options Data.xlsx")
        check_excel_file()
    else:
        check_excel_file()
    print("Input stock tickers separated by a space, the quotes and trades for each stock will be streamed")
    print("When you are done entering tickers, press Enter to show the quotes for each stock in order")
    stock_tickers = input('Enter Ticker(s): ').upper().split()
    #############################################################################################################
    websocket.enableTrace(True)
    websocket_token = "bsq43v0fkcbdt6un6ivg"
    websocket_url = "wss://ws.finnhub.io?token=" + websocket_token
    socket = websocket.WebSocketApp(websocket_url, on_message=on_message, on_error=on_error, on_close=on_close)
    socket.on_open = on_open
    #############################################################################################################
    key = "PK5S3WI3U5I3OBCZV82C"
    sec = "xfR7UlCNxngZbkriUvyIrk2rFNvR89IPw9epAK3d"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')
    account = api.get_account()
    account_balance = float(account.buying_power) / 4
    api.cancel_all_orders()
    api.close_all_positions()
    print('Trading Account status:', account.status)
    date = dt.datetime.date(dt.datetime.now(dt.timezone.utc))
    # Get when the market opens or opened today
    print('The date is:', str(dt.date.today()), 'The time is', str(dt.datetime.now().time()), 'CST')
    clock = api.get_clock()
    market_close = str(clock.next_close)[:16:] + str(':00.000000')
    print("The market closes at {} o'clock EST today.".format(market_close[11:16:]),
          "Extended hours trading lasts for 4 hours before and after regular market hours.")
    #############################################################################################################
    try:
        while True:
            start = time.time()
            stock_buylist = {}
            stock_shortlist = {}
            stock_prices = {}
            strongbuy = {}
            buy = {}
            weakbuy = {}
            weaksell = {}
            sell = {}
            strongsell = {}
            volume_terms = {}
            trade_data = {}
            ti_data = {}
            quote_data = {}
            stock_list_length = {}
            orders = []
            stock_price_movement = {}
            indicator_votes = {}
            options_seesaw = {}
            for ticker in stock_tickers:
                indicator_votes[ticker] = {'Bullish Votes': 0, 'Bearish Votes': 0, 'Neutral Votes': 0}
                trade_data[ticker] = []
                ti_data[ticker] = []
                quote_data[ticker] = []
                stock_buylist[ticker] = []
                stock_shortlist[ticker] = []
                stock_price_movement[ticker] = []
    ############################################################################################################
            while True:
                check()
                print('List of open positions:', api.list_positions())
                main_data_engine()
                print('Trades:', trade_data)
                print('Quotes:', quote_data)
                print('Indicators:', ti_data)
                if not check_trades():
                    print('Warning! No trades gathered! Program restarting...')
                    break
                ##############################
                ticker_operations()
                volume_operations()
                analysis_operations()
                trade_execution_operations()
                end = time.time()
                print('Time Elapsed (in seconds):', int((end - start)))
                cleanup()
    except Exception as e:
        print(e)
        raise Exception('An error has occurred...')
    finally:
        print('All pending orders will be cancelled and all positions will be liquidated immediately')
        api.cancel_all_orders()
        api.close_all_positions()
