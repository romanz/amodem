import numpy as np


class IIR:
    def __init__(self, b, a):
        self.b = np.array(b) / a[0]
        self.a = np.array(a[1:]) / a[0]
        self.x_state = [0] * len(self.b)
        self.y_state = [0] * (len(self.a) + 1)

    def __call__(self, x):
        x_, y_ = self.x_state, self.y_state
        for v in x:
            x_ = [v] + x_[:-1]
            y_ = y_[:-1]
            num = np.dot(x_, self.b)
            den = np.dot(y_, self.a)
            y = num - den
            y_ = [y] + y_
            yield y
        self.x_state, self.y_state = x_, y_


def lfilter(b, a, x):
    f = IIR(b=b, a=a)
    y = list(f(x))
    return np.array(y)
