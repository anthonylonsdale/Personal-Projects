import math
import matplotlib.pyplot as plt
import numpy as np

def AW(x):
    z = 2*x
    return (-1) * np.exp((-2 / 3) * (-z) ** (3/2))


if __name__ == '__main__':
    Xo = -5.0
    Xf = 20
    step = 0.001
    len = int((Xf - Xo) / step)
    s = 2
    x = [0.0 for i in range(len)]
    W = [0.0 for i in range(len)]
    W[0] = AW(Xo)
    W[1] = AW(Xo + step)
    W[2] = AW(Xo + 2 * step)
    x[0] = Xo
    x[1] = Xo + step
    x[2] = Xo + 2 * step
    while (s+2) < len:
        W[s+2] = -W[s-1] + W[s] + W[s+1] - 2 * step ** 2 * (2 * x[s]) * W[s]
        x[s+1] = Xo + (s+1) * step
        s += 1
    s = 0

    xaxis = np.arange(Xo, Xf, step)
    fig = plt.figure()
    plt.plot(xaxis, W, "r")
    fig.gca().set_ylabel('arb. units')
    fig.gca().set_xlabel('arb. units')
    plt.title(r'$\phi$(x)')
    plt.show()

    while s < len:
        W[s] = W[s] ** 2
        s += 1

    xaxis = np.arange(Xo, Xf, step)

    fig = plt.figure()
    plot = plt.plot(xaxis, W, "g")
    fig.gca().set_ylabel('arb. units')
    fig.gca().set_xlabel('arb. units')
    plt.title(r'|$\phi$(x)|$^{2}$')

    plt.show()
