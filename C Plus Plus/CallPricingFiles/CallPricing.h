#pragma once

#ifdef CallPricing_EXPORTS
#define CallPricing __declspec(dllexport)
#else
#define CallPricing __declspec(dllimport)
#endif

extern "C" CallPricing int main(int argc, char** argv);
