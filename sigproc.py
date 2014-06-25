import numpy as np
from numpy import linalg

def lfilter(b, a, x):
    b = np.array(b) / a[0]
    a = np.array(a[1:]) / a[0]

    x_ = [0] * len(b)
    y_ = [0] * len(a)
    for v in x:
        x_ = [v] + x_[:-1]
        u  = np.dot(x_, b)
        u = u - np.dot(y_, a)

        y_ = [u] + y_[1:]
        yield u


class Filter(object):
    def __init__(self, b, a):
        self.b = b
        self.a = a

    def apply(self, x):
        return lfilter(self.b, self.a, x)

    @classmethod
    def train(cls, S, training):
        A = np.array([ S[1:], S[:-1], training[:-1] ]).T
        b = training[1:]
        b0, b1, a1 = linalg.lstsq(A, b)[0]
        return cls([b0, b1], [1, -a1])


class QAM(object):
    def __init__(self, bits_per_symbol, radii):
        self._enc = {}
        index = 0
        N = (2 ** bits_per_symbol) / len(radii)
        for a in radii:
            for i in range(N):
                k = tuple(int(index & (1 << j) != 0) for j in range(bits_per_symbol))
                v = np.exp(2j * i * np.pi / N)
                self._enc[k] = v * a
                index += 1
        self._dec = {v: k for k, v in self._enc.items()}
        self.points = self._enc.values()
        self.bits_per_symbol = bits_per_symbol

    def encode(self, bits):
        trailing_bits = len(bits) % self.bits_per_symbol
        if trailing_bits:
            bits = bits + [0] * (self.bits_per_symbol - trailing_bits)
        for i in range(0, len(bits), self.bits_per_symbol):
            s = self._enc[ tuple(bits[i:i+self.bits_per_symbol]) ]
            yield s

    def decode(self, symbols):
        keys = np.array(self._dec.keys())
        for s in symbols:
            index = np.argmin(np.abs(s - keys))
            yield self._dec[ keys[index] ]

modulator = QAM(bits_per_symbol=4, radii=[0.6, 1.0])

class Resampler(object):
    def __init__(self, factor, )

def test():
    q = QAM(bits_per_symbol=8, radii=[0.25, 0.5, 0.75, 1.0])
    bits = [(1,1,0,1,0,0,1,0)]
    S = q.encode(bits)
    res = list(q.decode(list(S)))
    assert res == bits, (res)
