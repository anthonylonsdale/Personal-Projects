#include "pch.h"
#include <iostream>
#include <algorithm>

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
float sqrt2(const float x)
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

DLLEXPORT double CallPricing(float s, float k, float rf, float t, float v)
{
    double Option_Price, u, d, q, rfr;

    // 1 divided by 265 is .00273973, delta is again divided by the size of the array giving us .000027397
    const double divisor = 0.000027973;

    const double delta = t * divisor;

    u = std::exp(v * sqrt2(delta));
    d = 1 / u;
    rfr = std::exp(rf * delta);
    q = (rfr - d) / (u - d);

    auto* stockTree = new double[101][101];
    for (int i = 0;i <= 100;i++)
    {
        for (int j = 0;j <= i;j++)
        {
            stockTree[i][j] = s * std::pow(u, 2 * j - i);
        }
    }
    auto* valueTree = new double[101][101];
    for (int j = 0;j <= 100;j++)
    {
        valueTree[100][j] = max(stockTree[100][j] - k, 0.);
    }
    delete[]stockTree;
    for (int i = 99;i >= 0;i--)
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

DLLEXPORT double PutPricing(float Spot, float Strike, float Rate, float Time, float Sigma)
{
    double Option_Price, u, d, q, rfr;

    // 1 divided by 265 is .00273973, delta is again divided by the size of the array giving us .000027397
    const double divisor = 0.000027973;

    const double delta = Time * divisor;

    u = std::exp(Sigma * sqrt2(delta));
    d = 1 / u;
    rfr = std::exp((Rate)*delta);
    q = (rfr - d) / (u - d);

    auto* stockTree = new double[101][101];
    for (int i = 0;i <= 100;i++)
    {
        for (int j = 0;j <= i;j++)
        {
            stockTree[i][j] = Spot * std::pow(u, 2 * j - i);
        }
    }
    auto* valueTree = new double[101][101];
    for (int j = 0;j <= 100;j++)
    {
        valueTree[100][j] = max(Strike - stockTree[100][j], 0.);
    }
    delete[]stockTree;
    for (int i = 99;i >= 0;i--)
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
