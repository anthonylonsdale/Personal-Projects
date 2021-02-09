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


def on_message(ws, message):
    if message == '{"type":"ping"}':
        return
    data = loads(message)
    stock_fundamentals = data['data'][0]
    time_integer = stock_fundamentals['t']
    timestamp = dt.datetime.fromtimestamp(time_integer / 1e3)
    timestamp = str("{}.{:03d}".format(timestamp.strftime('%Y-%m-%d %H:%M:%S'), timestamp.microsecond // 1000))
    stock_fundamentals['t'] = timestamp
    s = stock_fundamentals['s']
    stock_fundamentals['time'] = stock_fundamentals.pop('t')
    stock_fundamentals['price'] = stock_fundamentals.pop('p')
    stock_fundamentals['stock'] = stock_fundamentals.pop('s')
    stock_fundamentals['volume'] = stock_fundamentals.pop('v')
    print(stock_fundamentals)
    trade_data[s].append(stock_fundamentals)


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
    AddReference(r"C:\Users\fabio\source\repos\Webscraper Class Library\Webscraper Class Library\bin\Debug\Web"
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
            dividend = div[div.find(delimiter1) + 1: div.find(delimiter2)]
            if dividend == 'N/A':
                dividend = 0
            else:
                div_string = dividend.split("%")[0]
                dividend = float(div_string) / 100
            quote['dividend'] = dividend
        if (i % 6) == 5:
            st = str(stock_info[i])
            quote['stock'] = st
            quote['time'] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            quote_data[st].append(quote)
            quote = {}
            df_quote = DataFrame(quote_data[st])
            df_quote.set_index('time', inplace=True)
            print(df_quote)


def tech_indicators():
    resolution = ['1', '5', '15', '30', '60', 'D', 'W', 'M']
    for st in stock_tickers:
        i = 0
        while True:
            try:
                timestamp_tech = time.strftime("%Y-%m-%d %H:%M:%S")
                tech_url = 'https://finnhub.io/api/v1/scan/technical-indicator?symbol=' + st + \
                           '&resolution=' + resolution[i] + '&token=bsq43v0fkcbdt6un6ivg'
                r = get(tech_url)
                ti = r.json()
                technical = ti['technicalAnalysis']['count']
                technical['signal'] = ti['technicalAnalysis']['signal']
                technical['adx'] = ti['trend']['adx']
                technical['trending'] = ti['trend']['trending']
                technical['time'] = timestamp_tech
                ti_data[st].append(technical)
                df_tech = DataFrame(ti_data[st])
                df_tech.set_index('signal', inplace=True)
                print(df_tech)
            except KeyError:
                if i == 7:
                    break
                i += 1
            break


def main_data_engine():
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
        time.sleep(15)
        socket.keep_running = False
        socket.close()
        t1.join()
        t2.join()
        t3.join()
    except Exception as error:
        print(error)
        socket.close()


def ticker_operations():
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
    for element in stock_tickers:
        volume_past_30sec = 0
        volume_past_min = 0
        volume_past_2min = 0
        volume_past_5min = 0
        stock_price = 0
        stock_list_length[element] = 0
        length = []
        stock_prices[element] = []
        for pos, ite in enumerate(trade_data[element]):
            if pos >= int(len(trade_data[element]) - 25):
                stock_price += ite['price']
                length.append(ite)
                stock_list_length[element] = int(len(length))
            ##############################################################################
            tradetime = dt.datetime.strptime(ite['time'], "%Y-%m-%d %H:%M:%S.%f")
            if tradetime > dt.datetime.now() - dt.timedelta(seconds=30):
                volume_past_30sec += int(ite['volume'])
            if tradetime > dt.datetime.now() - dt.timedelta(seconds=60):
                volume_past_min += int(ite['volume'])
            if tradetime > dt.datetime.now() - dt.timedelta(seconds=120):
                volume_past_2min += int(ite['volume'])
            if tradetime > dt.datetime.now() - dt.timedelta(seconds=300):
                volume_past_5min += int(ite['volume'])
        ##############################################################################
        stock_prices[element] = float("{:.3f}".format(stock_price / stock_list_length[element]))
        volume_terms[element] = volume_past_30sec, volume_past_min, volume_past_2min, volume_past_5min
        ##############################################################################
    print('volume by stock ordered 30sec, 1min, 2min and 5min:', volume_terms)
    print('stock prices:', stock_prices)


# might need rework and additional analysis
def analysis_operations():
    # this block is only to see if the stock has had an increase or decrease in short term price respectively
    # if the following conditions are met, then this represents a good trade opportunity
    # this portion works
    for sto in stock_buylist:
        for pos, i in enumerate(quote_data[sto]):
            if dt.datetime.strptime(quote_data[sto][pos]['time'], "%Y-%m-%d %H:%M:%S") > \
                    (dt.datetime.now() - dt.timedelta(minutes=5)):
                if pos == (len(quote_data[sto]) - 1) and quote_data[sto][pos]['current price'] < \
                        stock_prices[sto]:
                    stock_price_movement[sto] = 'short-term increase in price'
    for sto in stock_shortlist:
        for pos, i in enumerate(quote_data[sto]):
            if dt.datetime.strptime(quote_data[sto][pos]['time'], "%Y-%m-%d %H:%M:%S") > \
                    (dt.datetime.now() - dt.timedelta(minutes=5)):
                # if current price is lower than quote price
                if pos == (len(quote_data[sto]) - 1) and quote_data[sto][pos]['current price'] > \
                        stock_prices[sto]:
                    stock_price_movement[sto] = 'short-term decrease in price'
    print(stock_price_movement)
    ##############################################################################
    for element in stock_price_movement:
        if 'increase' in stock_price_movement[element]:
            if len(stock_buylist[element]) > 2:
                if quote_data[element][-1]['current price'] > quote_data[element][-2]['current price'] > \
                        quote_data[element][-3]['current price']:
                    if 'Very Bullish' in stock_buylist[element][-1] and 'Very Bullish' in stock_buylist[element][-2]:
                        strong_buy.append(element)
                elif quote_data[element][-1]['current price'] > quote_data[element][-2]['current price']:
                    if 'Bullish' in stock_buylist[element][-1] and 'Bullish' in stock_buylist[element][-2]:
                        buy.append(element)
                else:
                    weak_buy.append(element)
        if 'decrease' in stock_price_movement[element]:
            if len(stock_shortlist[element]) > 2:
                if quote_data[element][-1]['current price'] < quote_data[element][-2]['current price'] < \
                        quote_data[element][-3]['current price']:
                    if 'Very Bearish' in stock_shortlist[element][-1] and 'Very Bearish' in element:
                        strong_sell.append(element)
                elif quote_data[element][-1]['current price'] < quote_data[element][-2]['current price']:
                    if 'Bearish' in stock_shortlist[element][-1] and 'Bearish' in stock_shortlist[element][-2]:
                        sell.append(element)
                else:
                    weak_sell.append(element)
        ##############################################################################
    if len(strong_buy) > 0:
        print('Stock Strong Buy List:', strong_buy)
    if len(buy) > 0:
        print('Stock Buy List:', buy)
    if len(weak_buy) > 0:
        print('Stock Weak Buy List:', weak_buy)
    if len(strong_sell) > 0:
        print('Stock Strong Sell List:', strong_sell)
    if len(sell) > 0:
        print('Stock Sell List:', sell)
    if len(weak_sell) > 0:
        print('Stock Weak Sell List:', weak_sell)


def trade_execution_operations():
    global strong_buy, buy, weak_buy, strong_sell, sell, weak_sell, current_stock_position
    print(api.list_orders())
    block_purchase = []

    if len(api.list_positions()) > 0:
        for stockticker in stock_tickers:
            try:
                stock_position = api.get_position(stockticker)
                print(stock_position)
                position_value = getattr(stock_position, "market_value")
                position_value = abs(float(position_value))
                if position_value >= (0.10 * account_balance):
                    block_purchase.append('block ' + stockticker)
            except Exception as problem:
                print(problem)
                continue

        for element in strong_buy:
            try:
                # for an element in the strong_buy indicator list, if it is equal to the current stock position,
                # then we wont liquidate, if not then we will liquidate
                if element in current_stock_position:
                    continue
                else:
                    # if we have an indicator that is different that we just calculated, we need to remove
                    # the old position and use the new analysis as it is more up to date on the strength of the stock
                    check_orders = api.list_orders(status='open')
                    for order in check_orders:
                        api.cancel_order(order.id)
                    api.close_position(element)
            except Exception as problem:
                print(problem)
                continue

        for element in buy:
            try:
                if element in current_stock_position:
                    continue
                else:
                    check_orders = api.list_orders(status='open')
                    for order in check_orders:
                        api.cancel_order(order.id)
                    api.close_position(element)
            except Exception as problem:
                print(problem)
                continue

        for element in weak_buy:
            try:
                if element in current_stock_position:
                    continue
                else:
                    check_orders = api.list_orders(status='open')
                    for order in check_orders:
                        api.cancel_order(order.id)
                    api.close_position(element)
            except Exception as problem:
                print(problem)
                continue

        for element in strong_sell:
            try:
                if element in current_stock_position:
                    continue
                else:
                    check_orders = api.list_orders(status='open')
                    for order in check_orders:
                        api.cancel_order(order.id)
                    api.close_position(element)
            except Exception as problem:
                print(problem)
                continue

        for element in sell:
            try:
                if element in current_stock_position:
                    continue
                else:
                    check_orders = api.list_orders(status='open')
                    for order in check_orders:
                        api.cancel_order(order.id)
                    api.close_position(element)
            except Exception as problem:
                print(problem)
                continue

        for element in weak_sell:
            try:
                if element in current_stock_position:
                    continue
                else:
                    check_orders = api.list_orders(status='open')
                    for order in check_orders:
                        api.cancel_order(order.id)
                    api.close_position(element)
            except Exception as problem:
                print(problem)
                continue

    #################################################################################################################
    # check orders and see if they should be sold, if we have idle bracket orders with a small fluctuating profit/loss
    # just close them out
    for element in stock_tickers:
        api.list_positions()
        for stockposition in api.list_positions():
            if float(getattr(stockposition, "unrealized_intraday_plpc")) > 0.001:
                check_orders = api.list_orders(status='open')
                for order in check_orders:
                    api.cancel_order(order.id)
                api.close_position(element)

    #################################################################################################################
    # code is necessary to import the c# trading program
    AddReference(r"C:\Users\fabio\source\repos\Main Trade Executor Class Library\Main Trade Executor Class Lib"
                 r"rary\bin\Release\Main Trade Executor Class Library.dll")
    import CSharpTradeExecutor
    trader = CSharpTradeExecutor.BracketOrders()

    print(block_purchase)

    for element in strong_buy:
        try:
            for pos, it in enumerate(block_purchase):
                if element in block_purchase[pos]:
                    raise Exception('{} Position has exceeded 10% of the portfolio value'.format(element))
            price = stock_prices[element]
            account_percentage = (account_balance * 0.04) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            stop_loss = 0.9985 * price
            stoplosslimitprice = .9980 * price
            limit_price = 1.002 * price
            args = [element, 'buy', str(round_lot), str(round(stop_loss, 2)), str(round(limit_price, 2)),
                    str(round(stoplosslimitprice, 2))]
            trader.Trader(args)
            notification.show_toast("Program Trades Executed", "Program executed strongbuy trade of {} at {}".format(
                                    element, time.strftime("%H:%M:%S")), duration=4)
            pos = str(element + 'strongbuy')
            current_stock_position.append(pos)
        except Exception as error:
            print('There was an {} with the trade execution'.format(error))
            continue
    strong_buy = []

    for element in buy:
        try:
            for pos, it in enumerate(block_purchase):
                if element in block_purchase[pos]:
                    raise Exception('{} Position has exceeded 10% of the portfolio value'.format(element))
            price = stock_prices[element]
            account_percentage = (account_balance * 0.03) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = 1.0016 * price
            stop_loss = 0.9986 * price
            stoplosslimitprice = 0.9984 * price
            args = [element, 'buy', str(round_lot), str(round(stop_loss, 2)), str(round(limit_price, 2)),
                    str(round(stoplosslimitprice, 2))]
            trader.Trader(args)
            notification.show_toast("Program Trades Executed", "Program executed buy trade of {} at {}".format(
                                    element, time.strftime("%H:%M:%S")), duration=4)
            pos = str(element + 'buy')
            current_stock_position.append(pos)
        except Exception as error:
            print('There was an {} with the trade execution'.format(error))
            continue
    buy = []

    for element in weak_buy:
        try:
            for pos, it in enumerate(block_purchase):
                if element in block_purchase[pos]:
                    raise Exception('{} Position has exceeded 10% of the portfolio value'.format(element))
            price = stock_prices[element]
            account_percentage = (account_balance * 0.025) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = 1.0012 * price
            stop_loss = 0.9988 * price
            stoplosslimitprice = 0.9986 * price
            args = [element, 'buy', str(round_lot), str(round(stop_loss, 2)), str(round(limit_price, 2)),
                    str(round(stoplosslimitprice, 2))]
            trader.Trader(args)
            notification.show_toast("Program Trades Executed", "Program executed weakbuy trade of {} at {}".format(
                                    element, time.strftime("%H:%M:%S")), duration=4)
            pos = str(element + 'weakbuy')
            current_stock_position.append(pos)
        except Exception as error:
            print('There was an {} with the trade execution'.format(error))
            continue
    weak_buy = []

    # short trades
    for element in strong_sell:
        try:
            for pos, it in enumerate(block_purchase):
                if element in block_purchase[pos]:
                    raise Exception('{} Position has exceeded 10% of the portfolio value'.format(element))
            price = stock_prices[element]
            account_percentage = (account_balance * 0.04) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = .998 * price
            stop_loss = 1.0015 * price
            stoplosslimitprice = 1.0020 * price
            args = [element, 'sell', str(round_lot), str(round(stop_loss, 2)), str(round(limit_price, 2)),
                    str(round(stoplosslimitprice, 2))]
            trader.Trader(args)
            notification.show_toast("Program Trades Executed", "Program executed strongsell trade of {} at {}".format(
                                    element, time.strftime("%H:%M:%S")), duration=4)
            pos = str(element + 'strongsell')
            current_stock_position.append(pos)
        except Exception as error:
            print('There was an {} with the trade execution'.format(error))
            continue
    strong_sell = []

    for element in sell:
        try:
            for pos, it in enumerate(block_purchase):
                if element in block_purchase[pos]:
                    raise Exception('{} Position has exceeded 10% of the portfolio value'.format(element))
            price = stock_prices[element]
            account_percentage = (account_balance * 0.03) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = .9984 * price
            stop_loss = 1.0012 * price
            stoplosslimitprice = 1.0016 * price
            args = [element, 'sell', str(round_lot), str(round(stop_loss, 2)), str(round(limit_price, 2)),
                    str(round(stoplosslimitprice, 2))]
            trader.Trader(args)
            notification.show_toast("Program Trades Executed", "Program executed sell trade of {} at {}".format(
                                    element, time.strftime("%H:%M:%S")), duration=4)
            pos = str(element + 'sell')
            current_stock_position.append(pos)
        except Exception as error:
            print('There was an {} with the trade execution'.format(error))
            continue
    sell = []

    for element in weak_sell:
        try:
            for pos, it in enumerate(block_purchase):
                if element in block_purchase[pos]:
                    raise Exception('{} Position has exceeded 10% of the portfolio value'.format(element))
            price = stock_prices[element]
            account_percentage = (account_balance * 0.025) // price
            round_lot = int(account_percentage)
            if round_lot == 0:
                round_lot += 1
            limit_price = .9988 * price
            stop_loss = 1.0010 * price
            stoplosslimitprice = 1.0012 * price
            args = [element, 'sell', str(round_lot), str(round(stop_loss, 2)), str(round(limit_price, 2)),
                    str(round(stoplosslimitprice, 2))]
            trader.Trader(args)
            notification.show_toast("Program Trades Executed", "Program executed weaksell trade of {} at {}".format(
                                    element, time.strftime("%H:%M:%S")), duration=4)
            pos = str(element + 'weaksell')
            current_stock_position.append(pos)
        except Exception as error:
            print('There was an {} with the trade execution'.format(error))
            continue
    weak_sell = []


def check_trades():
    if len(trade_data) == 0:
        print('No trades were gathered')
        return False
    return True


def cleanup():
    # get rid of elements in lists that are dated 5 minutes and beyond to save memory
    if (end - start) > 300:
        for element in stock_tickers:
            for p, i in enumerate(trade_data[element]):
                if dt.datetime.strptime(i['time'], "%Y-%m-%d %H:%M:%S.%f") < \
                        dt.datetime.now() - dt.timedelta(seconds=300):
                    trade_data[element].remove(i)
            for po, it in enumerate(quote_data[element]):
                if dt.datetime.strptime(it['time'], "%Y-%m-%d %H:%M:%S") < \
                        dt.datetime.now() - dt.timedelta(seconds=300):
                    quote_data[element].remove(it)
            for pos, ite in enumerate(ti_data[element]):
                if dt.datetime.strptime(ite['time'], "%Y-%m-%d %H:%M:%S") < \
                        dt.datetime.now() - dt.timedelta(seconds=300):
                    ti_data[element].remove(ite)


def check():
    close = dt.datetime.strptime(market_close, '%Y-%m-%d %H:%M:%S.%f')
    if local_timezone == 'EST':
        if dt.datetime.now() > (close - dt.timedelta(minutes=1)):
            api.close_all_positions()
            api.cancel_all_orders()
            raise Exception('The market is closing in 1 minute, all positions have been closed')
    if local_timezone == 'CST':
        if dt.datetime.now() > (close - dt.timedelta(minutes=61)):
            api.close_all_positions()
            api.cancel_all_orders()
            raise Exception('The market is closing in 1 minute, all positions have been closed')


if __name__ == '__main__':
    key = "PKCPC6RJ84BG84W3PB60"
    sec = "U1r9Z2QknL9FwAaTztfLl5g1DTxpa5m97qyWCGZ7"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')
    #############################################################################################################
    notification = ToastNotifier()
    websocket.enableTrace(True)
    websocket_url = "wss://ws.finnhub.io?token=bsq43v0fkcbdt6un6ivg"
    socket = websocket.WebSocketApp(websocket_url, on_message=on_message, on_error=on_error, on_close=on_close)
    socket.on_open = on_open
    #############################################################################################################
    account = api.get_account()
    account_balance = float(account.buying_power) / 4
    print('Trading Account status:', account.status)
    date = dt.datetime.date(dt.datetime.now(dt.timezone.utc))
    # Get when the market opens or opened today
    fulltimezone = str(dt.datetime.now(dt.timezone.utc).astimezone().tzinfo)
    local_timezone = ''.join([c for c in fulltimezone if c.isupper()])
    print('The date is:', str(dt.date.today()), 'The time is', str(dt.datetime.now().time()), local_timezone)
    clock = api.get_clock()
    market_close = str(clock.next_close)[:16:] + str(':00.000000')
    print("The market closes at {} o'clock EST today.".format(market_close[11:16:]))
    print("Input stock tickers separated by a space, the quotes and trades for each stock will be streamed")
    print("When you are done entering tickers, press Enter to show the quotes for each stock in order")
    print("Enter in 'close' in order to close all current positions")
    stock_tickers = input('Enter Ticker(s): ').upper().split()
    ####################################################################################################################
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

    try:
        while True:
            start = time.time()
            stock_buylist = {}
            stock_shortlist = {}
            stock_prices = {}
            volume_terms = {}
            trade_data = {}
            ti_data = {}
            quote_data = {}
            stock_list_length = {}
            indicator_votes = {}
            current_stock_position = []
            stock_price_movement = {}
            for ticker in stock_tickers:
                indicator_votes[ticker] = {'Bullish Votes': 0, 'Bearish Votes': 0, 'Neutral Votes': 0}
                trade_data[ticker] = []
                ti_data[ticker] = []
                quote_data[ticker] = []
                stock_buylist[ticker] = []
                stock_shortlist[ticker] = []
                stock_price_movement[ticker] = ''
            ############################################################################################################
            while True:
                strong_buy = []
                buy = []
                weak_buy = []
                weak_sell = []
                sell = []
                strong_sell = []
                tradethread = th.Thread(target=trade_execution_operations)
                tradethread.daemon = True
                check()
                main_data_engine()
                print('Trades:', trade_data)
                print('Quotes:', quote_data)
                print('Indicators:', ti_data)
                if not check_trades():
                    print('Warning, No trades gathered! Program terminating...')
                    raise SystemExit(0)
                ##############################
                ticker_operations()
                volume_operations()
                analysis_operations()
                tradethread.start()
                end = time.time()
                print('Time Elapsed (in seconds):', int((end - start)))
                cleanup()
                tradethread.join()
    # except Exception as e:
        # notification.show_toast("Program Error", "Program Raised Error {}".format(e), duration=5)
    finally:
        print('All pending orders will be cancelled and all positions will be liquidated immediately')
        api.cancel_all_orders()
        api.close_all_positions()
