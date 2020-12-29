using System;
using System.Threading.Tasks;
using Alpaca.Markets;

namespace CSharpTradeExecutor
{
    public class BracketOrders
    {
        public static async Task Trader(String[] args)
        {
            String symbol = args[1];
            String side = args[2];
            int round_lot = int.Parse(args[3]);
            long stopLossStopPrice = long.Parse(args[4]);
            long takeProfitLimitPrice = long.Parse(args[5]);
            long stopLossLimitPrice = long.Parse(args[6]);

            var tradingClient = Environments.Paper.GetAlpacaTradingClient(new SecretKey("PKCPC6RJ84BG84W3PB60", "U1r9Z2QknL9FwAaTztfLl5g1DTxpa5m97qyWCGZ7"));

            if (side == "buy")
            {
                await tradingClient.PostOrderAsync(MarketOrder.Buy(symbol, round_lot).WithDuration(TimeInForce.Gtc).Bracket(stopLossStopPrice: stopLossStopPrice, takeProfitLimitPrice: takeProfitLimitPrice, stopLossLimitPrice: stopLossLimitPrice));

            }
            if (side == "sell")
            {
                await tradingClient.PostOrderAsync(MarketOrder.Sell(symbol, round_lot).WithDuration(TimeInForce.Gtc).Bracket(stopLossStopPrice: stopLossStopPrice, takeProfitLimitPrice: takeProfitLimitPrice, stopLossLimitPrice: stopLossLimitPrice));

            }

            Console.WriteLine("Trade has been executed");
        }
    }
}
