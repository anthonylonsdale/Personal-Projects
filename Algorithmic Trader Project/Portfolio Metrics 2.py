import alpaca_trade_api as trade_api
import datetime as dt
import pandas as pd
import numpy as np
import time

if __name__ == '__main__':
    pd.options.mode.chained_assignment = None
    key = "PKCPC6RJ84BG84W3PB60"
    sec = "U1r9Z2QknL9FwAaTztfLl5g1DTxpa5m97qyWCGZ7"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')
    # Get a list of filled orders.
    # Can also limit the results by date if desired.

    spec_date = dt.datetime.today() - dt.timedelta(days=27)
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

    # Total Net Profit for Long and Short Trades

    # filtering out bull long purchases
    long_purchases_df = activities_df.loc[(activities_df['side'] == 'buy') & (activities_df['cumulative_sum'] > 0)]
    # print(long_purchases)
    # long_purchases.to_excel("long purchases.xlsx")
    total_long_purchases = long_purchases_df['net_trade'].sum()
    print("Gross cost of long positions:", total_long_purchases)

    # filtering out bear 'buy to cover' purchases
    short_purchases_df = activities_df.loc[(activities_df['side'] == 'buy') & (activities_df['cumulative_sum'] <= 0)]
    # print(short_purchases)
    # short_purchases.to_excel("short purchases.xlsx")
    total_short_purchases = short_purchases_df['net_trade'].sum()
    print("Gross cost of short positions:", total_short_purchases)

    # filtering bull long sales
    long_sales_df = activities_df.loc[activities_df['side'] == 'sell']
    # print(long_sales)
    # long_sales.to_excel("long sales.xlsx")
    total_long_sells = long_sales_df['net_trade'].sum()
    print("Gross profit of long positions:", total_long_sells)

    # filtering bear short purchases
    short_sales_df = activities_df.loc[activities_df['side'] == 'sell_short']
    # print(short_sales)
    # short_sales.to_excel("short sales.xlsx")
    total_short_sells = short_sales_df['net_trade'].sum()
    print("Gross profit of short positions:", total_short_sells)

    net_long_position_pl = round(total_long_purchases + total_long_sells, 2)
    net_short_position_pl = round(total_short_purchases + total_short_sells, 2)
    print("Net profit of long positions:", net_long_position_pl)
    print("Net profit of short positions:", net_short_position_pl)

    activities_df.to_excel("Portfolio Activities Test.xlsx")
    ###################################################################################################################
    # gross profit and loss
    # for this we need to correlate the buys with the sells, which may be difficult
    long_buy_df = long_purchases_df.sort_values(['symbol', 'transaction_time'])
    lb_df = pd.DataFrame(long_buy_df)
    lb_df.reset_index(drop=True, inplace=True)
    # lb_df.to_excel("test grouping buy.xlsx")
    print(lb_df)

    long_sales_df = long_sales_df.sort_values(['symbol', 'transaction_time'])
    ls_df = pd.DataFrame(long_sales_df)
    ls_df.reset_index(drop=True, inplace=True)
    # ls_df.to_excel("test grouping sell.xlsx")
    print(ls_df)

    # we can make an order book that tracks each trade as it iterates down the list
    # example: first buy is 18 shares of appl
    buy_order_book = {}
    for index, row in lb_df.iterrows():
        # we only need type (fill or partial fill), net_trade, cumulative_sum, net_qty and symbol
        # print(row)
        buy_order_book[index] = [row['transaction_time'], row['type'], row['qty'], round(row['net_trade'], 2),
                                 row['cumulative_sum']]
    print(len(buy_order_book), buy_order_book)

    sell_order_book = {}
    for index, row in ls_df.iterrows():
        # we only need net_trade, cumulative_sum, net_qty and symbol
        # print(row)
        sell_order_book[index] = [row['transaction_time'], row['type'], row['qty'], round(row['net_trade'], 2),
                                  row['cumulative_sum']]
    print(len(sell_order_book), sell_order_book)

    trade_book = {}
    current_buy_pos = 0
    current_sell_pos = 0
    ###################################################################################################################
    for position, item in enumerate(buy_order_book.copy(), start=current_buy_pos):
        try:
            position = current_buy_pos
            # print(current_buy_pos)
            # first we need to settle all the partial fills and combine them into a single trade
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
            # print(position)
            # print(current_buy_pos)
            # print(buy_order_book)
            # print('-------------------------------------------------------------------------------------------------')
        except KeyError:
            pass
    print(len(buy_order_book), buy_order_book)

    for position, item in enumerate(sell_order_book.copy(), start=current_sell_pos):
        try:
            position = current_sell_pos
            # print(current_sell_pos)
            # first we need to settle all the partial fills and combine them into a single trade
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
            # print(position)
            # print(current_sell_pos)
            # print(sell_order_book)
            # print('-------------------------------------------------------------------------------------------------')
        except KeyError:
            pass
    print(len(sell_order_book), sell_order_book)

    # now that we have settled all buy and sell orders, its time to correlate them and determine profit/ loss
    position = 0
    current_buy_pos = 0
    current_sell_pos = 0
    trade_ledger_position = 0

    while len(buy_order_book) > 0:
        for position, item in enumerate(buy_order_book.copy(), start=current_buy_pos):
            # print(position)
            # print(current_buy_pos)
            # print(current_sell_pos)

            # start with the very basic, if we have a direct match, and the cumulative sell = 0 (meaning there is no
            # net position), then that is a buy trade and sell trade matched up together
            if buy_order_book[current_buy_pos][2] == sell_order_book[current_sell_pos][2]:
                trade_book[trade_ledger_position] = round(buy_order_book[current_buy_pos][3] +
                                                          sell_order_book[current_sell_pos][3], 2)
                del buy_order_book[current_buy_pos], sell_order_book[current_sell_pos]

            else:
                while True:
                    # first we figure the value of each share in the purchase
                    bought_share_value = round(buy_order_book[current_buy_pos][3] / buy_order_book[current_buy_pos][2], 2)
                    sold_share_value = round(sell_order_book[current_sell_pos][3] / sell_order_book[current_sell_pos][2], 2)
                    buy_quantity = buy_order_book[current_buy_pos][2]
                    sell_quantity = sell_order_book[current_sell_pos][2]
                    buy_val = buy_order_book[current_buy_pos][3]
                    sell_val = sell_order_book[current_sell_pos][3]

                    # print(bought_share_value)
                    # print(sold_share_value)
                    if buy_quantity > sell_quantity:
                        value_of_shares_sold = bought_share_value * sell_quantity
                        # print(value_of_shares_sold)
                        trade_book[trade_ledger_position] = round(value_of_shares_sold + sell_val, 2)
                        buy_order_book[current_buy_pos][2] -= sell_quantity
                        buy_order_book[current_buy_pos][3] = round(buy_val - value_of_shares_sold, 2)
                        buy_order_book[current_buy_pos][4] -= sell_quantity
                        del sell_order_book[current_sell_pos]
                        break

                    # for debugging: time.sleep(1)
                    if buy_quantity < sell_quantity:
                        # print("#################################################")
                        # this one will be a bit harder, we need to add up buy orders until we match the sell order
                        value_of_shares_sold = sold_share_value * buy_quantity
                        # print(value_of_shares_sold)

                        sell_order_book[current_sell_pos][2] -= buy_quantity
                        sell_order_book[current_sell_pos][3] = round(sell_val - value_of_shares_sold, 2)
                        del buy_order_book[current_buy_pos]
                        # print(buy_val)
                        # print(value_of_shares_sold)
                        trade_book[trade_ledger_position] = round(value_of_shares_sold + buy_val, 2)
                    break

            if len(buy_order_book) > 0:
                # print(buy_order_book)
                # print(sell_order_book)
                # print(trade_book)
                # every path will need to settle back down here
                current_buy_pos = list(buy_order_book)[0]
                current_sell_pos = list(sell_order_book)[0]
                current_buy_pos = int(current_buy_pos)
                current_sell_pos = int(current_sell_pos)
                trade_ledger_position += 1

    ###################################################################################################################
    print(trade_book)
    net_profit = 0
    for i in range(len(trade_book)):
        # print(trade_book[i])
        net_profit += trade_book[i]
    net_long_profit = round(net_profit, 2)
    
    # profit per symbol
    net_zero_trades = activities_df.groupby('symbol').filter(lambda trades: sum(trades.net_qty) == 0)
    trades = net_zero_trades.groupby('symbol').net_trade
    profit_per_symbol = net_zero_trades.groupby('symbol').net_trade.sum()
    print(profit_per_symbol)
