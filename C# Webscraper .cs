using System;
using System.Linq;
using System.Collections.Generic;

namespace CSharpwebscraper
{
    public class Webscraper
    {
        public static void Main(String[] args)
        {
            Console.WriteLine("Enter Stock Tickers separated by a space:");
            String[] stock_tickers = Console.ReadLine().ToUpper().Split(' ');
            HtmlAgilityPack.HtmlWeb web = new HtmlAgilityPack.HtmlWeb();
            IDictionary<string, List<string>> Stock_Attributes = new Dictionary<string, List<string>>();
            for (int i = 0; i < stock_tickers.Length; i++)
            {
                String ticker = stock_tickers[i];
                String url = "https://finance.yahoo.com/quote/" + ticker + "?p=" + ticker;
                HtmlAgilityPack.HtmlDocument doc = web.Load(url);
                var Quote = doc.DocumentNode.SelectNodes("//span[@class='Trsdu(0.3s) Fw(b) Fz(36px) Mb(-4px) D(ib)']").ToList();
                foreach (var item in Quote)
                {
                    string price = item.InnerText;
                    String consoleoutput = ticker + " Stock Price: " + price;
                    Console.WriteLine(consoleoutput);
                    if (!Stock_Attributes.ContainsKey(stock_tickers[i]))
                    {
                        Stock_Attributes.Add(stock_tickers[i], new List<string>());
                    }
                    Stock_Attributes[stock_tickers[i]].Add(price);
                }
                var Indicator = doc.DocumentNode.SelectNodes("//span[@data-reactid='53']").ToList();
                foreach (var item in Indicator)
                {
                    if (item == Indicator[1])
                    {
                        string indicator = item.InnerText;
                        String consoleoutput = ticker + " Stock Indicator: " + indicator;
                        Console.WriteLine(consoleoutput);
                        Stock_Attributes[stock_tickers[i]].Add(indicator);
                    }
                }
                var Previous_Close = doc.DocumentNode.SelectNodes("//td[@data-test='PREV_CLOSE-value']").ToList();
                foreach (var item in Previous_Close)
                {
                    string prev_price = item.InnerText;
                    String consoleoutput = ticker + " Stock Previous Close Price: " + prev_price;
                    Console.WriteLine(consoleoutput);
                    Stock_Attributes[stock_tickers[i]].Add(prev_price);
                }
                var Open = doc.DocumentNode.SelectNodes("//td[@data-test='OPEN-value']").ToList();
                foreach (var item in Open)
                {
                    string open_price = item.InnerText;
                    String consoleoutput = ticker + " Stock Open Price: " + item.InnerText;
                    Console.WriteLine(consoleoutput);
                    Stock_Attributes[stock_tickers[i]].Add(open_price);
                }
            }
        foreach(String key in Stock_Attributes.Keys)
        {
            Console.WriteLine(key);
            foreach(String item in Stock_Attributes[key]) 
            {
                Console.Write("{0}, ", item);
            }
        }
        }
    }
}
