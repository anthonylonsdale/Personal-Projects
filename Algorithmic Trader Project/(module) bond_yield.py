from requests import get
from bs4 import BeautifulSoup
import pandas as pd
import openpyxl
"""
The methodology will be expanded upon later but essentially
we can take a look at changing bond prices as an indicator
of market volatility, if bond prices increase then that
signals more investors are purchasing bonds, causing
yields to decrease, and the opposite is true.
"""


def treasury_bond_yields():
    bond_yields = {}
    r = get("https://www.treasury.gov/resource-center/data-chart-center/interest-rates/Pages/TextView.aspx?data=yield")
    soup = BeautifulSoup(r.text, 'lxml')
    bond_list = [entry.text for entry in soup.find_all('td', {'class': 'text_view_data'})]

    date = None
    for i in range(len(bond_list)):
        if i % 13 == 0:
            date = bond_list[i]
            bond_yields[date] = []
            continue
        bond_yields[date].append(bond_list[i])

    bond_df = pd.DataFrame.from_dict(bond_yields).T
    bond_df = bond_df.rename(columns={0: '1 Mo', 1: '2 Mo', 2: '3 Mo', 3: '6 Mo', 4: '1 Yr', 5: '2 Yr',
                                      6: '3 Yr', 7: '5 Yr', 8: '7 Yr', 9: '10 Yr', 10: '20 Yr', 11: '30 Yr'})
    string_date = date.replace("/", '-')
    url = f"C:/Users/fabio/PycharmProjects/AlgoTrader/ALGO/Daily Stock Analysis/Bonds/T-Bonds Data {string_date}.xlsx"
    wb = openpyxl.Workbook()
    wb.save(url)
    book = openpyxl.load_workbook(url)
    writer = pd.ExcelWriter(url, engine='openpyxl')
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    bond_df.to_excel(writer, sheet_name=f"Treasury Bonds for {string_date}")
    try:
        sheet = book['Sheet']
        book.remove(sheet)
    except KeyError:
        pass
    book.save(url)


if __name__ == "__main__":
    treasury_bond_yields()
