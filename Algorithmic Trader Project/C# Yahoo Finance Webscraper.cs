using System;
using System.Linq;
using System.Collections.Generic;
using HtmlAgilityPack;

namespace CSharpwebscraper
{
    public class Webscraper
    {
        public List<string> Scraper(String[] stock_tickers)
        {
            HtmlWeb web = new HtmlWeb();
            var Stock_Info = new List<string> { };
            for (int i = 0; i < stock_tickers.Length; i++)
            {
                String ticker = stock_tickers[i];
                String url = "https://finance.yahoo.com/quote/" + ticker + "?p=" + ticker;
                HtmlDocument doc = web.Load(url);
                var Quote = doc.DocumentNode.SelectNodes("//span[@class='Trsdu(0.3s) Fw(b) Fz(36px) Mb(-4px) D(ib)']").ToList();
                foreach (var item in Quote)
                {
                    string price = item.InnerText;
                    String consoleoutput = ticker + " Stock Price: " + price;
                    Console.WriteLine(consoleoutput);
                    Stock_Info.Add(price);
                }
                
                var Previous_Close = doc.DocumentNode.SelectNodes("//td[@data-test='PREV_CLOSE-value']").ToList();
                foreach (var item in Previous_Close)
                {
                    string prev_price = item.InnerText;
                    String consoleoutput = ticker + " Stock Previous Close Price: " + prev_price;
                    Console.WriteLine(consoleoutput);
                    Stock_Info.Add(prev_price);
                }
                var Open = doc.DocumentNode.SelectNodes("//td[@data-test='OPEN-value']").ToList();
                foreach (var item in Open)
                {
                    string open_price = item.InnerText;
                    String consoleoutput = ticker + " Stock Open Price: " + open_price;
                    Console.WriteLine(consoleoutput);
                    Stock_Info.Add(open_price);
                }
                var Indicator = doc.DocumentNode.SelectNodes("//div[@class='Fz(xs) Mb(4px)']").ToList();
                foreach (var item in Indicator)
                {
                    string indicator = item.InnerText;
                    int index = indicator.IndexOf("p");
                    if (index > 0)
                        indicator = indicator.Substring(0, index);
                    String consoleoutput = ticker + " Stock Indicator: " + indicator;
                    Console.WriteLine(consoleoutput);
                    Stock_Info.Add(indicator);
                }
                var Yield = doc.DocumentNode.SelectNodes("//td[@data-test='DIVIDEND_AND_YIELD-value']").ToList();
                foreach (var item in Yield)
                {
                    string dividend = item.InnerText;
                    String consoleoutput = ticker + " Stock Dividend/Yield: " + dividend;
                    Console.WriteLine(consoleoutput);
                    Stock_Info.Add(dividend);
                }
                Stock_Info.Add(ticker);
            }
            return Stock_Info;
        }
    }
}
