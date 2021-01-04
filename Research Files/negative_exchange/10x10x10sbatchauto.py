#!/usr/bin/env python

import os

if __name__ == '__main__':
  temperature = 50
  for i in range(1,21):
    temp = int(temperature) * i
    if temp == 1000:
        temp_string = "99_1000"
    else:
        temp_string = str(temp)
        
    filename = "PyTestSub_{}k".format(temp_string)
    
    os.system("sbatch {}".format(filename))
    