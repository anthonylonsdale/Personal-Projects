from clr import AddReference
import datetime as dt


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
        for index, item in enumerate(inital_stock_info):
            if item in self.stock_tickers:
                current_stock = item
                continue
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
            initial_data[current_stock].append(item)
            if index % 10 == 9:
                initial_data[current_stock].append(dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return initial_data

    def quote_data_processor(self):
        scraped_stock_info = self.scrape_client.Scraper(self.stock_tickers)
        quote_data = {}
        for stock in self.stock_tickers:
            quote_data[stock] = []

        current_stock = None
        for index, item in enumerate(scraped_stock_info):
            if item in self.stock_tickers:
                current_stock = item
                continue
            if index % 6 == 1:
                item = item.replace(',', '')
                item = float(item)
            quote_data[current_stock].append(item)

        return quote_data
