import math


def _g(rd):
    return 1 / math.sqrt(1 + 3 * math.pow(rd, 2) / math.pow(math.pi, 2))


class Player:

    def get_rating(self):
        return (self.__rating * 173.7178) + 1500

    def get_rd(self):
        return self._rd * 173.7178

    def __init__(self, rating=None, rd=None, vol=0.06, tau=0.5):
        self.__rating = (rating - 1500) / 173.7178
        self._rd = rd / 173.7178
        self.vol = vol
        self._tau = tau

    def _pre_rating_rd(self):
        self._rd = math.sqrt(math.pow(self._rd, 2) + math.pow(self.vol, 2))

    def update_player(self, rating_list, rd_list, outcome_list):
        rating_list = [(x - 1500) / 173.7178 for x in rating_list]
        rd_list = [x / 173.7178 for x in rd_list]

        v = self._v(rating_list, rd_list)
        self.vol = self._new_vol(rating_list, rd_list, outcome_list, v)
        self._pre_rating_rd()

        self._rd = 1 / math.sqrt((1 / math.pow(self._rd, 2)) + (1 / v))

        temp_sum = 0
        for i in range(len(rating_list)):
            temp_sum += _g(rd_list[i]) * (outcome_list[i] - self._e(rating_list[i], rd_list[i]))
        self.__rating += math.pow(self._rd, 2) * temp_sum

    def _new_vol(self, rating_list, rd_list, outcome_list, v):
        a_vol = math.log(self.vol**2)
        eps = 0.000001
        a = a_vol

        delta = self._delta(rating_list, rd_list, outcome_list, v)
        tau = self._tau
        if (delta ** 2) > ((self._rd ** 2) + v):
            b = math.log(delta ** 2 - self._rd ** 2 - v)
        else:
            k = 1
            while self._f(a_vol - k * math.sqrt(tau**2), delta, v, a_vol) < 0:
                k += 1
            b = a_vol - k * math.sqrt(tau**2)

        f_a = self._f(a, delta, v, a_vol)
        f_b = self._f(b, delta, v, a_vol)

        while math.fabs(b - a) > eps:
            c = a + ((a - b) * f_a)/(f_b - f_a)
            f_c = self._f(c, delta, v, a_vol)
            if f_c * f_b < 0:
                a = b
                f_a = f_b
            else:
                f_a = f_a/2.0
            b = c
            f_b = f_c
        return math.exp(a / 2)

    def _f(self, x, delta, v, a):
        ex = math.exp(x)
        num1 = ex * (delta**2 - self.__rating**2 - v - ex)
        denom1 = 2 * ((self.__rating**2 + v + ex)**2)
        return (num1 / denom1) - ((x - a) / (self._tau**2))

    def _delta(self, rating_list, rd_list, outcome_list, v):
        temp_sum = 0
        for i in range(len(rating_list)):
            temp_sum += _g(rd_list[i]) * (outcome_list[i] - self._e(rating_list[i], rd_list[i]))
        return v * temp_sum

    def _v(self, rating_list, rd_list):
        temp_sum = 0
        for i in range(len(rating_list)):
            temp_e = self._e(rating_list[i], rd_list[i])
            temp_sum += math.pow(_g(rd_list[i]), 2) * temp_e * (1 - temp_e)
        return 1 / temp_sum

    def _e(self, p2rating, p2_rd):
        return 1 / (1 + math.exp(-1 * _g(p2_rd) * (self.__rating - p2rating)))
