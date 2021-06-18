#include "pch.h"
#include <iostream>
#include <immintrin.h>
#include <math.h>
#include <vector>

#define DLLEXPORT extern "C" __declspec(dllexport)
#define SQRT_MAGIC_F 0x5f3759df 

/*
file was specifically built using no external dependencies!!
compiled using x64 architecture and only x64
main entry point for this file is the CallPricing function, which is called as a DLL from
my python program using CTYPEs in order to price options contracts very quickly.
The intention is to keep this c plus plus file as fast and lean as possible due to the
magnitude of calculations we have to perform. 1000 iterations seems to strike an optimal
balance between pricing accuracy and speed.
*/

float  sqrt2(const float x)
{
    const float xhalf = 0.5f * x;

    union // get bits for floating value
    {
        float x;
        int i;
    } u;
    u.x = x;
    u.i = SQRT_MAGIC_F - (u.i >> 1);  // gives initial guess y0
    return x * u.x * (1.5f - xhalf * u.x * u.x); // Newton step, repeating increases accuracy 
}

DLLEXPORT double CallPricing(float Spot, float Strike, float Rate, float Time, float Sigma, float Yield)
{
    double Option_Price, u, d, q, rfr;

    const int n = 500;
    Time = Time / 365;
    const float delta = Time / n;

    u = std::exp(Sigma * sqrt2(delta));
    d = 1 / u;
    rfr = std::exp((Rate - Yield) * delta);
    q = (rfr - d) / (u - d);
    // create storage for the stock price tree and option price tree
    auto* stockTree = new double[n + 1][n + 1];
    // setup and initialise the stock price tree
    for (int i = 0;i <= n;i++)
    {
        for (int j = 0;j <= i;j++)
        {
            stockTree[i][j] = Spot * std::pow(u, 2 * j - i);
        }
    }
    auto* valueTree = new double[n + 1][n + 1];

    for (int j = 0;j <= n;j++)
    {
        valueTree[n][j] = max(stockTree[n][j] - Strike, 0.);
    }
    delete[]stockTree;

    for (int i = n - 1;i >= 0;i--)
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

DLLEXPORT double PutPricing(float Spot, float Strike, float Rate, float Time, float Sigma, float Yield)
{
    double Option_Price, u, d, q, rfr;
    const int n = 500;

    Time = Time / 365;
    const float delta = Time / n;
    u = std::expf(Sigma * sqrt2(delta));
    d = 1 / u;
    rfr = std::exp((Rate - Yield) * delta);
    q = (rfr - d) / (u - d);

    auto* stockTree = new double[n + 1][n + 1];
    for (int i = 0;i <= n;i++)
    {
        for (int j = 0;j <= i;j++)
        {
            stockTree[i][j] = Spot * std::pow(u, 2 * j - i);
        }
    }
    auto* valueTree = new double[n + 1][n + 1];
    for (int j = 0;j <= n;j++)
    {
        valueTree[n][j] = max(Strike - stockTree[n][j], 0.);
    }
    delete[]stockTree;
    for (int i = n - 1;i >= 0;i--)
    {
        for (int j = 0;j <= i;j++)
        {
            valueTree[i][j] = exp(-Rate * delta) * (q * valueTree[i + 1][j + 1] + (1 - q) * valueTree[i + 1][j]);
        }
    }
    Option_Price = valueTree[0][0];
    delete[]valueTree;
    return Option_Price;
}

int main(int argc, char** argv)
{
    return 0;
}
