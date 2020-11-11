#include <iostream>
#include <cmath>
#include <vector>
#include <sstream>

int main(int argc, char** argv)
{
  // seven argument in total
  double Spot=0.00, Strike=0.00, Rate=0.00, Time = 0.00, Sigma=0.00, Dividend = 0.00;
  int iterations=0;
  for (int i = 1; i < argc; i++) {
        //std::cout << argv[i] << std::endl;
        std::string input = argv[i];
        std::stringstream ss = std::stringstream(input);
        if (i == 1)
        {
          ss >> Spot;
        }
        if (i == 2)
        {
          ss >> Strike;
        }
        if (i == 3)
        {
          ss >> Rate;
        }
        if (i == 4)
        {
          ss >> Time;
        }
        if (i == 5)
        {
          ss >> Sigma;
        }
        if (i == 6)
        {
          ss >> Dividend;
        }
        if (i == 7)
        {
          ss >> iterations;
        }
    }

  double Option_Price = 0.;
  
  double delta, u, d, q;

  Time = Time / 365;
  delta = Time / iterations;
  u = exp(Sigma*sqrt(delta));
  d = 1 / u;
  q = (exp((Rate-Dividend) * delta)-d)/(u-d);
  // create storage for the stock price tree and option price tree
  std::vector<std::vector<double>> stockTree(iterations+1,std::vector<double>(iterations+1));
  // setup and initialise the stock price tree
  for(int i=0;i<=iterations;i++)
  {
    for(int j=0;j<=i;j++)
    {
      stockTree[i][j]=Spot*pow(u,j)*pow(d,i-j);
    }
  }
  std::vector<std::vector<double>> valueTree(iterations+1,std::vector<double>(iterations+1));
  
  for(int j=0;j<=iterations;j++)
      {
        valueTree[iterations][j]= std::max(Strike - stockTree[iterations][j],0.);
      }
  for(int i=iterations-1;i>=0;i--)
  {
    for(int j=0;j<=i;j++)
    {
      valueTree[i][j] = exp(-Rate*delta)*( q*valueTree[i+1][j+1] + (1-q)*valueTree[i+1][j]);
    }
  }
  Option_Price = valueTree[0][0];
  //std::cout << "Calculated price using "<<iterations<<" iterations is " << Stock_Price << std::endl;
  std::cout << Option_Price;
}
