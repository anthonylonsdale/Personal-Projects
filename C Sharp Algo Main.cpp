#include <string>
#include <iostream>
#include <vector>
#include <iterator>
#include <algorithm>

void printing_stock_inputs(std::string input, std::string delimiter)
{
    // getting each ticker and printing it (does not change input)
    std::vector<std::string> stock_tickers;
    size_t last = 0;
    size_t next = 0;
    while ((next = input.find(delimiter, last)) != std::string::npos) 
    {
        std::cout << input.substr(last, next-last) << std::endl;
        stock_tickers.push_back(input.substr(last, next-last));
        last = next ++;
    }
    std::cout << input.substr(last) << std::endl;

}

int main() 
{
    // getting string
    std::string input;
    std::cout << "Enter stock tickers separated by a space: \n";
    std::getline(std::cin, input);
    std::string delimiter = " ";
    printing_stock_inputs(input, delimiter);
    return 0;
}

