#include "pch.h"
#include <iostream>
#include <cmath>
#include <vector>
#include <sstream>

using namespace std;

#define DLLEXPORT extern "C" __declspec(dllexport)

DLLEXPORT double CallPricing(double Spot, double Strike, double Rate, double Time, double Sigma, double Yield, int iterations)
{
    double Option_Price;

    double delta, u, d, q;

    Time = Time / 365;
    delta = Time / iterations;
    u = exp(Sigma * sqrt(delta));
    d = 1 / u;
    q = (exp((Rate - Yield) * delta) - d) / (u - d);
    // create storage for the stock price tree and option price tree
    vector<vector<double>> stockTree(iterations + 1, vector<double>(iterations + 1));
    // setup and initialise the stock price tree
    for (int i = 0;i <= iterations;i++)
    {
        for (int j = 0;j <= i;j++)
        {
            stockTree[i][j] = Spot * pow(u, j) * pow(d, i - j);
        }
    }
    vector<vector<double>> valueTree(iterations + 1, vector<double>(iterations + 1));

    for (int j = 0;j <= iterations;j++)
    {
        valueTree[iterations][j] = max(stockTree[iterations][j] - Strike, 0.);
    }
    for (int i = iterations - 1;i >= 0;i--)
    {
        for (int j = 0;j <= i;j++)
        {
            valueTree[i][j] = exp(-Rate * delta) * (q * valueTree[i + 1][j + 1] + (1 - q) * valueTree[i + 1][j]);
        }
    }
    Option_Price = valueTree[0][0];
    //std::cout << "Calculated price using "<<iterations<<" iterations is " << Stock_Price << std::endl;
    cout << Option_Price;
    return Option_Price;
}


int main(int argc, char** argv)
{
    return 0;
}
