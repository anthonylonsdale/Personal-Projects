import matplotlib.pyplot as plt
import numpy as np
import random as random
import scipy.stats as stats

def v(p):
    return (p * h) / (m * L)


def sigpos(p):
    return ((L ** 2) / (8 * np.pi)) * (
            (A21 ** 2) / ((A21 ** 2) / 4 + (4 * (np.pi ** 2)) * (
            detuning + (v(p)) / L) ** 2))


def signeg(p):
    return ((L ** 2) / (8 * np.pi)) * (
            (A21 ** 2) / ((A21 ** 2) / 4 + (4 * (np.pi ** 2)) * (
            detuning - (v(p)) / L) ** 2))


def probpos(p):
    return (flux * sigpos(p)) / (A21 + 2 * (flux * sigpos(p) + flux * signeg(
        p)))


def probneg(p):
    return (flux * signeg(p)) / (A21 + 2 * (flux * sigpos(p) + flux * signeg(
        p)))


def maxboltz():
    unit = (h ** 2) / (L ** 2)
    for i in range(1, 200):
        distributionarray[i] = C * np.exp(-(((i - 99) ** 2) * (unit)) / (2 * m * k * T))

    return distributionarray


if __name__ == '__main__':
    A21 = 4.27 * 10 ** 7
    m = 1.16 * 10 ** (-26)
    k = 1.3807 * 10 ** (-23)
    L = 671 * 10 ** (-9)
    flux = (1 * (A21 * 2 * np.pi) / (L ** 2))
    detuning = A21 / (2 * np.pi)
    h = 6.6261 * 10 ** -34
    T = 1 * 10 ** (-3)

    distributionarray = [0] * 200

    momentumarray = [0] * 200

    xaxis = np.arange(-100, 100, 1)

    p = 0

    P1 = probpos(p)
    P2 = probneg(p)

    for _ in range(100000):

        Q = random.random()

        if Q < P1:
            p = p + 1
        elif Q > (1 - P2):
            p = p - 1
        elif P1 < Q < (1 - P2):
            p = p

        P1 = probpos(p)
        P2 = probneg(p)

        momentumarray[p + 100] = momentumarray[p + 100] + 1

    C = momentumarray[100]
    unit = (h ** 2) / (L ** 2)
    for i in range(1, 200):
        distributionarray[i] = C * np.exp(-(((i - 100) ** 2) * (unit)) / (2 * m * k * T))

    maxwell = stats.maxwell

    params = maxwell.fit(momentumarray, loc=0)

    params = (0, (params[1] * (10 ** -6)))

    label = "Maxwell-Boltzmann Fit, Temp:" + str(params[1] / 2.1)
    # plot = plt.plot(xaxis, maxwell.pdf(xaxis, *params), label=label, color='orange', lw=3)

    plt.plot(xaxis, maxboltz(), label="Maxwell-Boltzmann Fit", color='orange', lw=2)
    plt.bar(xaxis, momentumarray, label="Number of Lithium Atoms", color='black')
    plt.xlabel("Momentum of Lithium Particles")
    plt.ylabel('Atoms')

    plt.title("Plot With 5 Times Flux and Normal Detuning")
    plt.legend()
    plt.show()
