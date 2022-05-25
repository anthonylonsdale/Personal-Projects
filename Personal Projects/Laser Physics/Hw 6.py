import math
import matplotlib.pyplot as plt


if __name__ == '__main__':
    a21 = 10 ** 7
    a1 = 10 ** 8
    n2 = 10 / 11
    n1 = 1 / 11
    r1 = 1
    r2 = 0.97
    l = 0.1
    e = 2.718281828459045
    #######################################################
    wavelength = 500 * (10 ** -9)
    sigma = ((wavelength ** 2) / (2 * 3.141592653)) * (a21 / (a21 + a1))  # photon area
    resonant_sigma = sigma * 0.9
    timestep = 10 ** -9
    pumpRate = 2 * -1 * (a1 * math.log(r2, e) + 2 * a1 * sigma * n2) / (2 * sigma * l)  # photons / second
    dimension = 5000
    #######################################################
    # initialize the arrays
    n1Array = [0] * dimension
    n2Array = [0] * dimension
    timeArray = [timestep] * dimension
    for i in range(dimension):
        timeArray[i] = timeArray[i] * i
    phiArray = [1] * dimension
    phiArray2 = [1] * dimension
    #######################################################
    for i in range(len(n1Array)):
        if phiArray[i] < 1:
            phiArray[i] = 1
        dn1dt = (a21 * n2Array[i]) - (a1 * n1Array[i]) + (phiArray[i] * sigma * (n2Array[i] - n1Array[i])) \
                                                       + (phiArray2[i] * resonant_sigma * (n2Array[i] - n1Array[i]))
        dn2dt = pumpRate - (a21 * n2Array[i]) - (phiArray[i] * sigma * (n2Array[i] - n1Array[i])) \
                                              - (phiArray2[i] * resonant_sigma * (n2Array[i] - n1Array[i]))

        dphidt = phiArray[i] * 1.5 * (10**8) * (math.log(r2, e) + (0.2 * sigma * (n2Array[i] - n1Array[i])))
        dphi2dt = phiArray2[i] * 1.5 * (10**8) * (math.log(r2, e) + (0.2 * resonant_sigma * (n2Array[i] - n1Array[i])))

        print(dn1dt)
        print(dn2dt)
        print(dphidt)
        print(dphi2dt)
        if i == 4999:
            break

        phiArray[i+1] = phiArray[i] + (timestep * dphidt)
        phiArray2[i+1] = phiArray2[i] + (timestep * dphi2dt)
        n1Array[i+1] = (n1Array[i] + (timestep * dn1dt))
        n2Array[i+1] = (n2Array[i] + (timestep * dn2dt))
    ########################################################
    print(n1Array)
    print(n2Array)
    print(phiArray)
    print(timeArray)

    x = timeArray
    y1 = n1Array
    y2 = n2Array
    y3 = phiArray
    y4 = phiArray2
    plt.plot(x, y1, label='N1')
    plt.plot(x, y2, label='N2')
    plt.plot(x, y3, label='Flux, Sigma = 1')
    plt.plot(x, y4, label='Flux, Sigma = 0.9')
    plt.legend()
    plt.show()
