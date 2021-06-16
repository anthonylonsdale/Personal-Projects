from requests import get
from bs4 import BeautifulSoup
"""
The methodology will be expanded upon later but essentially
we can take a look at changing bond prices as an indicator
of market volatility, if bond prices increase then that
signals more investors are purchasing bonds, causing
yields to decrease, and the opposite is true.
"""


class riskfreerate:
    def __init__(self):
        self.r = get('https://www.marketwatch.com/investing/bond/tmubmusd01m?countrycode=bx')

    def onemonthyield(self):
        soup = BeautifulSoup(self.r.text, 'lxml')
        bond_list = [entry.text for entry in
                     soup.find_all('bg-quote', {'channel': '/zigman2/quotes/211347041/realtime'})]
        bond_rate = float(bond_list[1])
        print("1 month risk-free-rate", str(bond_rate) + str('%'))
        return bond_rate
