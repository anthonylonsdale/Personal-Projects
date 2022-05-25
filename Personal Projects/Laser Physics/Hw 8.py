import math
import matplotlib.pyplot as plt


if __name__ == '__main__':
    a21 = 3 * 10 ** 6
    a1 = 0
    n2 = 10 / 11
    n1 = 1 / 11
    r1 = 1
    r2 = 0.04
    l = 0.1
    e = 2.718281828459045
    #######################################################
    wavelength = 500 * (10 ** -9)
    sigma = ((wavelength ** 2) / (2 * 3.141592653)) # photon area
    resonant_sigma = sigma * 0.9
    timestep = 10 ** -12 # picosecond
    pumpRate = 10 ** 24  # photons / second
    dimension = 2000000
    #######################################################
    # initialize the arrays
    n1Array = [0] * dimension
    n2Array = [0] * dimension
    timeArray = [timestep] * dimension
    for i in range(dimension):
        timeArray[i] = timeArray[i] * i
    phiArray = [0] * dimension
    #######################################################
    for i in range(len(n1Array)):
        if i >= 250000:
            if phiArray[i] < 1:
                phiArray[i] = 1
        dn1dt = (a21 * n2Array[i]) - (a1 * n1Array[i]) + (phiArray[i] * sigma * (n2Array[i] - n1Array[i]))
        dn2dt = pumpRate - (a21 * n2Array[i]) - (phiArray[i] * sigma * (n2Array[i] - n1Array[i]))

        dphidt = phiArray[i] * 1.5 * (10**8) * (math.log(r2, e) + (0.2 * sigma * (n2Array[i] - n1Array[i])))

        if i == 1999999:
            break

        phiArray[i+1] = phiArray[i] + (timestep * dphidt)
        n1Array[i+1] = (n1Array[i] + (timestep * dn1dt))
        n2Array[i+1] = (n2Array[i] + (timestep * dn2dt))
    ########################################################

    x = timeArray
    y1 = n1Array
    y2 = n2Array
    flux = phiArray
    #plt.plot(x, y1, label='N1')
    #plt.plot(x, y2, label='N2')
    plt.plot(x, flux, label='Flux')
    plt.legend()
    plt.show()
