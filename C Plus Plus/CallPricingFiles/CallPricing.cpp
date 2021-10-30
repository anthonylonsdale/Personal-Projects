#include "pch.h"
#include <iostream>
#include <vector>

#define DLLEXPORT extern "C" __declspec(dllexport)

/*
file was specifically built using no external dependencies!!
compiled using x64 architecture and only x64
main entry point for this file is the CallPricing function, which is called as a DLL from
my python program using CTYPEs in order to price options contracts very quickly.
The intention is to keep this c plus plus file as fast and lean as possible due to the
magnitude of calculations we have to perform. 500 iterations seems to strike an optimal
balance between pricing accuracy and speed.
*/

DLLEXPORT double CallPricing(float s, float k, float rf, float t, float v)
{
    double h, u, d;
    // the divisor is 1 / 365, the division is already computed
    const double divisor = 0.002738;
    int i, j;
    const int n = 500;
    auto* stkval = new double[n + 1][n + 1];

    h = t * .002 * divisor;
    u = std::exp(v * sqrt(2 * h));
    d = 1 / u;

    double pu = pow((exp(0.5 * rf * h) - exp(-v * sqrt(0.5 * h))) / (exp(v * sqrt(0.5 * h)) - exp(-v * sqrt(0.5 * h))), 2);
    double pd = pow((exp(v * sqrt(0.5 * h)) - exp(0.5 * rf * h)) / (exp(v * sqrt(0.5 * h)) - exp(-v * sqrt(0.5 * h))), 2);
    double pm = 1.0 - pu - pd;

    //q = (drift - d) / (u - d);

    // processing terminal stock price
    std::vector<std::vector<double> > S(2 * n + 1, std::vector<double>(n + 1));
    for (j = 0; j <= n; j++)
        for (i = 0; i <= 2 * j; i++)
            S[i][j] = s * pow(u, double(j - i));

    std::vector<std::vector<double> > V(2 * n + 1, std::vector<double>(n + 1));
    // Compute terminal payoffs
    for (i = 0; i <= 2 * n; i++) {
        V[i][n] = max(S[i][n] - k, 0.0);
    }

    for (j = n - 1; j >= 0; j--) {
        for (i = 0; i <= 2 * j; i++) {
             V[i][j] = max(S[i][j] - k, exp(-rf * h) * (pu * V[i][j + 1] + pm * V[i + 1][j + 1] + pd * V[i + 2][j + 1]));
        }
    }
    return V[0][0];
}

DLLEXPORT double PutPricing(float s, float k, float rf, float t, float v)
{
    double h, u, d;
    // the divisor is 1 / 365, the division is already computed
    const double divisor = 0.002738;
    int i, j;
    const int n = 500;
    auto* stkval = new double[n + 1][n + 1];

    h = t * .002 * divisor;
    u = std::exp(v * sqrt(2 * h));
    d = 1 / u;

    double pu = pow((exp(0.5 * rf * h) - exp(-v * sqrt(0.5 * h))) / (exp(v * sqrt(0.5 * h)) - exp(-v * sqrt(0.5 * h))), 2);
    double pd = pow((exp(v * sqrt(0.5 * h)) - exp(0.5 * rf * h)) / (exp(v * sqrt(0.5 * h)) - exp(-v * sqrt(0.5 * h))), 2);
    double pm = 1.0 - pu - pd;

    //q = (drift - d) / (u - d);

    // processing terminal stock price
    std::vector<std::vector<double> > S(2 * n + 1, std::vector<double>(n + 1));
    for (j = 0; j <= n; j++)
        for (i = 0; i <= 2 * j; i++)
            S[i][j] = s * pow(u, double(j - i));

    std::vector<std::vector<double> > V(2 * n + 1, std::vector<double>(n + 1));
    // Compute terminal payoffs
    for (i = 0; i <= 2 * n; i++) {
        V[i][n] = max(k - S[i][n], 0.0);
    }

    for (j = n - 1; j >= 0; j--) {
        for (i = 0; i <= 2 * j; i++) {
            V[i][j] = max(k - S[i][j], exp(-rf * h) * (pu * V[i][j + 1] + pm * V[i + 1][j + 1] + pd * V[i + 2][j + 1]));
        }
    }
    return V[0][0];
}

int main(int argc, char** argv)
{
    return 0;
}
