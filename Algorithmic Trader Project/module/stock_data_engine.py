from clr import AddReference
import datetime as dt
import requests
from bs4 import BeautifulSoup


def spy_returns():
    r = requests.get('https://finance.yahoo.com/quote/SPY?p=SPY')
    soup = BeautifulSoup(r.text, 'lxml')
    spy_returns_pct = [entry.text for entry in soup.find_all('span', {'data-reactid': '50'})]
    delimiter1 = '('
    delimiter2 = ')'
    formatted_return = str(spy_returns_pct[0])
    rt = formatted_return[formatted_return.find(delimiter1) + 1: formatted_return.find(delimiter2)]
    return_string = rt.split("%")[0]

    if return_string[0] == '+':
        spy_returns = '{:.2f}'.format(float(return_string.split('+')[1]))
    else:
        spy_returns = float(return_string)

    return spy_returns


class stockDataEngine:
    def __init__(self, stock_tickers=None):
        self.stock_tickers = stock_tickers
        AddReference(r"C:\Users\fabio\source\repos\Webscraper Class Library\Webscraper "
                     r"Class Library\bin\Debug\Webscraper Class Library.dll")
        import CSharpwebscraper
        self.scrape_client = CSharpwebscraper.Webscraper()

    def inital_quote_data_fetch(self):
        inital_stock_info = self.scrape_client.Initial(self.stock_tickers)
        initial_data = {}
        for stock in self.stock_tickers:
            initial_data[stock] = []

        current_stock = None
        quote = {}
        for index, item in enumerate(inital_stock_info):
            if item in self.stock_tickers:
                current_stock = item
                continue
            elem = item.replace(',', '')
            if index % 10 == 1:
                delimiter1 = '('
                delimiter2 = ')'
                div = str(item)
                dividend = div[div.find(delimiter1) + 1: div.find(delimiter2)]
                if dividend == 'N/A':
                    item = 0.00
                else:
                    div_string = dividend.split("%")[0]
                    dividend = float(div_string) / 100
                    item = round(dividend, 4)
                quote["dividend"] = item
            if index % 10 == 2:
                quote["day's range"] = elem
            if index % 10 == 3:
                quote["52 week range"] = elem
            if index % 10 == 4:
                quote["previous close"] = float(elem)
            if index % 10 == 5:
                quote["open"] = float(elem)
            if index % 10 == 6:
                quote["P/E ratio"] = float(elem) if not elem == 'N/A' else elem
            if index % 10 == 7:
                quote["average volume"] = int(elem)
            if index % 10 == 8:
                quote["one year target"] = float(elem)
            if index % 10 == 9:
                quote["beta"] = float(elem)
                quote["time"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                initial_data[current_stock].append(quote)
        return initial_data

    def quote_data_processor(self):
        scraped_stock_info = self.scrape_client.Scraper(self.stock_tickers)
        quote_data = {}
        for stock in self.stock_tickers:
            quote_data[stock] = []

        quote = {}
        current_stock = None
        for index, item in enumerate(scraped_stock_info):
            if item in self.stock_tickers:
                current_stock = item
                continue
            elem = item.replace(',', '')
            if index % 6 == 1:
                quote['current price'] = float(elem)
            if index % 6 == 2:
                quote['indicator'] = elem
            if index % 6 == 3:
                quote['volume'] = int(elem)
            if index % 6 == 4:
                quote['bid'] = elem
            if index % 6 == 5:
                quote['ask'] = elem
                quote['time'] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                quote_data[current_stock] = quote
        return quote_data
