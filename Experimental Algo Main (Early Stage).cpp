#include <vector>
#include <string>
#include <sstream>
#include <iostream>
#include <IEX.h>

/*
ideally i want to build a c plus plus version of the python algo trader when the python algo trader
is at completion (which is very close).
*/

std::vector<std::string> split(const std::string &s) {
    std::stringstream ss(s);
    std::string item;
    std::vector<std::string> stock_tickers;
    while (std::getline(ss, item, ' ')) {
        stock_tickers.push_back(item);
    }
    return stock_tickers;
}

int main()
{
    std::string line;
    int size = 0;
    std::cout << "Enter Stock Tickers Separated by a Space:";
    std::getline(std::cin, line);
    std::vector<std::string> stock_tickers = split(line);
    size = static_cast<int>(stock_tickers.size());
    for (int i = 0; i < size; i++)
    {
        std::cout << stock_tickers.at(i) << std::endl;
    }
    
    /* begin main driver code for the program
    here are the components that i will need
    1) input for the stock tickers and a way to isolate each ticker for input
    2) inputting each ticjer into the data streams (be it a stock trade stream or other)
    3) 
    */


}
