import alpaca_trade_api as trade_api
import datetime as dt
import pandas as pd
import numpy as np


def purchasing_filter(activities_df):
    # filtering out bull long purchases
    long_purchases_df = activities_df.loc[(activities_df['side'] == 'buy') & (activities_df['cumulative_sum'] > 0)]
    total_long_purchases = long_purchases_df['net_trade'].sum()
    print("Gross cost of long positions:", total_long_purchases)

    # filtering out bear 'buy to cover' purchases
    short_purchases_df = activities_df.loc[(activities_df['side'] == 'buy') & (activities_df['cumulative_sum'] <= 0)]
    total_short_purchases = short_purchases_df['net_trade'].sum()
    print("Gross cost of short positions:", total_short_purchases)

    # filtering bull long sales
    long_sales_df = activities_df.loc[activities_df['side'] == 'sell']
    total_long_sells = long_sales_df['net_trade'].sum()
    print("Gross profit of long positions:", total_long_sells)

    # filtering bear short purchases
    short_sales_df = activities_df.loc[activities_df['side'] == 'sell_short']
    total_short_sells = short_sales_df['net_trade'].sum()
    print("Gross profit of short positions:", total_short_sells)

    # net_long_position_pl = round(total_long_purchases + total_long_sells, 2)
    # net_short_position_pl = round(total_short_purchases + total_short_sells, 2)
    # print("Net profit of long positions:", net_long_position_pl)
    # print("Net profit of short positions:", net_short_position_pl)

    activities_df.to_excel("Portfolio Activities Test.xlsx")

    # gross profit and loss
    # for this we need to correlate the buys with the sells, which may be difficult
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
    short_order_time_held = {}
    long_order_time_held = {}
    ####################################################################################################################
    # adding to respective trade books
    current_buy_pos = 0
    current_sell_pos = 0
    short_trade_ledger_position = 0

    while len(short_buy_order_book) > 0:
        for position, item in enumerate(short_buy_order_book.copy(), start=current_buy_pos):
            d1 = dt.datetime.strptime(short_buy_order_book[current_buy_pos][0], "%Y-%m-%dT%H:%M:%S.%fZ")
            d2 = dt.datetime.strptime(short_sell_order_book[current_sell_pos][0], "%Y-%m-%dT%H:%M:%S.%fZ")
            elapsedTime = (d1 - d2).total_seconds()
            if short_buy_order_book[current_buy_pos][2] == short_sell_order_book[current_sell_pos][2]:
                short_trade_book[short_trade_ledger_position] = round(short_buy_order_book[current_buy_pos][3] +
                                                                      short_sell_order_book[current_sell_pos][3], 2)
                short_order_time_held[short_trade_ledger_position] = (elapsedTime, short_buy_order_book[current_buy_pos][2])
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
                        short_order_time_held[short_trade_ledger_position] = (elapsedTime, sell_quantity)
                        del short_sell_order_book[current_sell_pos]
                        break

                    if buy_quantity < sell_quantity:
                        value_of_shares_sold = sold_share_value * buy_quantity
                        short_sell_order_book[current_sell_pos][2] -= buy_quantity
                        short_sell_order_book[current_sell_pos][3] = round(sell_val - value_of_shares_sold, 2)
                        short_trade_book[short_trade_ledger_position] = round(value_of_shares_sold + buy_val, 2)
                        short_order_time_held[short_trade_ledger_position] = (elapsedTime, buy_quantity)
                        del short_buy_order_book[current_buy_pos]
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
            d1 = dt.datetime.strptime(buy_order_book[current_buy_pos][0], "%Y-%m-%dT%H:%M:%S.%fZ")
            d2 = dt.datetime.strptime(sell_order_book[current_sell_pos][0], "%Y-%m-%dT%H:%M:%S.%fZ")
            elapsedTime = (d2 - d1).total_seconds()
            if buy_order_book[current_buy_pos][2] == sell_order_book[current_sell_pos][2]:
                trade_book[trade_ledger_position] = round(buy_order_book[current_buy_pos][3] + sell_order_book[current_sell_pos][3], 2)
                long_order_time_held[trade_ledger_position] = (elapsedTime, buy_order_book[current_buy_pos][2])
                del buy_order_book[current_buy_pos], sell_order_book[current_sell_pos]

            else:
                while True:
                    bought_share_value = round(buy_order_book[current_buy_pos][3] / buy_order_book[current_buy_pos][2], 2)
                    sold_share_value = round(sell_order_book[current_sell_pos][3] / sell_order_book[current_sell_pos][2], 2)
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
                        long_order_time_held[trade_ledger_position] = (elapsedTime, sell_quantity)
                        del sell_order_book[current_sell_pos]
                        break

                    if buy_quantity < sell_quantity:
                        value_of_shares_sold = sold_share_value * buy_quantity
                        sell_order_book[current_sell_pos][2] -= buy_quantity
                        sell_order_book[current_sell_pos][3] = round(sell_val - value_of_shares_sold, 2)
                        trade_book[trade_ledger_position] = round(value_of_shares_sold + buy_val, 2)
                        long_order_time_held[trade_ledger_position] = (elapsedTime, buy_quantity)
                        del buy_order_book[current_buy_pos]
                    break

            if len(buy_order_book) > 0:
                current_buy_pos = list(buy_order_book)[0]
                current_sell_pos = list(sell_order_book)[0]
                trade_ledger_position += 1
    print(short_order_time_held)
    print(long_order_time_held)
    return short_trade_book, trade_book


if __name__ == '__main__':
    pd.options.mode.chained_assignment = None
    key = "PKCPC6RJ84BG84W3PB60"
    sec = "U1r9Z2QknL9FwAaTztfLl5g1DTxpa5m97qyWCGZ7"
    url = "https://paper-api.alpaca.markets"
    api = trade_api.REST(key, sec, url, api_version='v2')

    # Can also limit the results by date if desired.
    spec_date = dt.datetime.today() - dt.timedelta(days=31)
    date = spec_date.strftime('%Y-%m-%d')
    activities = api.get_activities(activity_types='FILL', date=date)
    activities_df = pd.DataFrame([activity._raw for activity in activities])
    activities_df = activities_df.iloc[::-1]
    stock_tickers_involved = list(set(activities_df['symbol'].tolist()))
    print(stock_tickers_involved)

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
    short_trade_book, trade_book = trade_book_settlement()
    ###################################################################################################################
    total_gross_profit = 0
    total_gross_loss = 0

    # print(short_trade_book)
    net_short_profit = 0
    total_short_trades = 0
    short_winning_trades = 0
    short_even_trades = 0
    short_losing_trades = 0
    for i in range(len(short_trade_book)):
        if short_trade_book[i] > 0:
            short_winning_trades += 1
            total_short_trades += 1
            total_gross_profit += short_trade_book[i]
        elif short_trade_book[i] < 0:
            short_losing_trades += 1
            total_short_trades += 1
            total_gross_loss += short_trade_book[i]
        else:
            short_even_trades += 1
            total_short_trades += 1
        net_short_profit += short_trade_book[i]
    net_short_profit = round(net_short_profit, 2)
    print("Short-side net profit:", net_short_profit)
    print("Short-side profitable trades:", short_winning_trades)
    print("Short-side even trades:", short_even_trades)
    print("Short-side Losing trades:", short_losing_trades)
    print("Total short-side trades:", total_short_trades)

    # print(trade_book)
    net_profit = 0
    total_long_trades = 0
    long_winning_trades = 0
    long_even_trades = 0
    long_losing_trades = 0
    for i in range(len(trade_book)):
        if trade_book[i] > 0:
            long_winning_trades += 1
            total_long_trades += 1
            total_gross_profit += trade_book[i]
        elif trade_book[i] < 0:
            long_losing_trades += 1
            total_long_trades += 1
            total_gross_loss += trade_book[i]
        else:
            long_even_trades += 1
            total_long_trades += 1
        net_profit += trade_book[i]
    net_long_profit = round(net_profit, 2)
    print("\nLong-side net profit:", net_long_profit)
    print("Long-side profitable trades:", long_winning_trades)
    print("Long-side even trades:", long_even_trades)
    print("Long-side losing trades:", long_losing_trades)
    print("Total long-side trades", total_long_trades)

    total_gross_profit = round(total_gross_profit, 2)
    total_gross_loss = round(total_gross_loss, 2)
    print("\nProfit Metrics:")
    print("Gross Profit:", total_gross_profit)
    print("Average Winning Trade:", round((total_gross_profit / (long_winning_trades + short_winning_trades)), 2))
    print("Gross Loss:", total_gross_loss)
    print("Average Losing Trade:", round((total_gross_loss / (total_long_trades + short_losing_trades)), 2))
    print("Total Net Profit:", round(total_gross_profit + total_gross_loss, 2))

    # profit per symbol
    net_zero_trades = activities_df.groupby('symbol').filter(lambda trades: sum(trades.net_qty) == 0)
    trades = net_zero_trades.groupby('symbol').net_trade
    profit_per_symbol = net_zero_trades.groupby('symbol').net_trade.sum()
    print("Net Profit per stock:")
    print(profit_per_symbol)
