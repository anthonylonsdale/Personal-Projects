#include "pch.h"
#include <iostream>
#include <algorithm>

#define DLLEXPORT extern "C" __declspec(dllexport)

/*
file was specifically built using no external dependencies!!
compiled using x64 architecture and only x64
main entry point for this file is the CallPricing function, which is called as a DLL from
my python program using CTYPEs in order to price options contracts very quickly.
The intention is to keep this c plus plus file as fast and lean as possible due to the
magnitude of calculations we have to perform. 1000 iterations seems to strike an optimal
balance between pricing accuracy and speed.
*/

DLLEXPORT double CallPricing(float s, float k, float rf, float t, float v)
{
    double Option_Price, u, d, q, rfr;

    // 1 divided by 365 is .00273973, delta is again divided by the size of the array giving us .000027397
    const double divisor = 0.00273973;

    const int n = 500;

    const double delta = t * divisor / n;

    u = std::exp(v * std::sqrt(delta));
    d = 1 / u;
    rfr = std::exp(rf * delta);
    q = (rfr - d) / (u - d);

    auto* stockTree = new double[n+1][n+1];
    for (int i = 0;i <= n;i++)
    {
        for (int j = 0;j <= i;j++)
        {
            stockTree[i][j] = s * std::pow(u, 2 * j - i);
        }
    }
    auto* valueTree = new double[n+1][n+1];
    for (int j = 0;j <= n;j++)
    {
        valueTree[n][j] = max(stockTree[n][j] - k, 0.);
    }
    delete[]stockTree;
    for (int i = n-1;i >= 0;i--)
    {
        for (int j = 0;j <= i;j++)
        {
            valueTree[i][j] = rfr * (q * valueTree[i + 1][j + 1] + (1 - q) * valueTree[i + 1][j]);
        }
    }
    Option_Price = valueTree[0][0];
    delete[]valueTree;
    return Option_Price;
}

DLLEXPORT double PutPricing(double s, double k, double rf, double t, double v)
{
    double h, u, d, drift, q;
    // the divisor is 1 / 365, the division is already computed
    const double divisor = 0.00273973;
    int i;
    const int n = 100;
    auto* stkval = new double[n + 1][n + 1];

    h = t * .01 * divisor;
    u = std::exp((rf - (0.5 * v * v)) * h + (v * std::sqrt(h)));
    d = std::exp((rf - (0.5 * v * v)) * h - (v * std::sqrt(h)));
    drift = std::exp(rf * h);
    q = (drift - d) / (u - d);

    // processing terminal stock price
    stkval[0][0] = s;
    for (int i = 1; i < n + 1; i++)
    {
        stkval[i][0] = stkval[i - 1][0] * u;
        for (int j = 1; j < i + 1; j++)
        {
            stkval[i][j] = stkval[i - 1][j - 1] * d;
        }
    }

    // backward recursion to obtain option_price
    auto* optval = new double[n + 1][n + 1];
    for (int j = 0; j < n + 1; j++)
    {
        optval[n][j] = max(0, k - stkval[n][j]);
    }
    for (int m = 0; m < n; m++)
    {
        i = n - m - 1;
        for (int j = 0; j < i + 1; j++)
        {
            optval[i][j] = (q * optval[i + 1][j] + (1 - q) * optval[i + 1][j + 1]) / drift;
            // check for early exercise
            optval[i][j] = max(optval[i][j], k - stkval[i][j]);
        }
    }
    double option_price = optval[0][0];
    delete[]stkval;
    delete[]optval;
    return option_price;
}

int main(int argc, char** argv)
{
    return 0;
}
