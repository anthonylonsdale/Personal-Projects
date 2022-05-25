import math
import matplotlib.pyplot as plt
import numpy as np


if __name__ == '__main__':
    a21 = 10 ** 7
    a21squared = a21 * a21
    lambda_res = 500 * (10 ** -9)
    lambda_res_squared = lambda_res * lambda_res
    pi = 3.141592653
    e = 2.718281828459045
    twopi = 2 * pi
    density = -1 * (20 * pi * math.log(0.9, e)) / (lambda_res ** 2)
    print(density)
    laser_intensity = 1
    sigma = lambda_res_squared / twopi

    x = np.linspace(-10**10, 10**10)

    phi = laser_intensity * ((twopi * a21) / lambda_res_squared)

    y = (1 / twopi) * math.sqrt(a21squared + ((a21 * phi * lambda_res_squared) / pi)) - \
         (((a21**3 * density*0.1*lambda_res_squared)/(4*twopi)) / (((a21squared*lambda_res_squared)/(2*twopi*sigma)) +
                                                                   (0.25 * a21squared) + (2*twopi*(x**2))))

    plt.plot(x, y, 'r')

    plt.show()


