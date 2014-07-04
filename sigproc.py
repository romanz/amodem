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

def train(S, training):
    A = np.array([ S[1:], S[:-1], training[:-1] ]).T
    b = training[1:]
    b0, b1, a1 = linalg.lstsq(A, b)[0]
    return lambda x: lfilter(b=[b0, b1], a=[1, -a1], x=x)

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

modulator = QAM(bits_per_symbol=2, radii=[1.0])

class Interpolator(object):
    def __init__(self, resolution=10000, width=128):
        self.width = width
        self.resolution = resolution
        self.N = resolution * width
        u = np.arange(-self.N, self.N, dtype=float)
        window = (1 + np.cos(0.5 * np.pi * u / self.N)) / 2.0
        h = np.sinc(u / resolution) * window
        self.filt = []
        for index in range(resolution):  # split into multiphase filters
            filt = h[index::resolution]
            filt = filt[::-1]
            self.filt.append(filt)
        lengths = map(len, self.filt)
        assert set(lengths) == set([2*width])
        assert len(self.filt) == resolution

    def get(self, offset):
        # offset = k + (j / self.resolution)
        k = int(offset)
        j = int((offset - k) * self.resolution)
        coeffs = self.filt[j]
        return coeffs, k - self.width

class Sampler(object):
    def __init__(self, src, interp):
        self.src = iter(src)
        self.freq = 1.0
        self.interp = interp
        coeffs, begin = self.interp.get(0)
        self.offset = -begin  # should fill samples buffer
        self.buff = np.zeros(len(coeffs))
        self.index = 0

    def __iter__(self):
        return self

    def correct(self, offset=0):
        assert self.freq + offset > 0
        self.offset += offset

    def next(self):
        res = self._sample()
        self.offset += self.freq
        return res

    def _sample(self):
        coeffs, begin = self.interp.get(self.offset)
        end = begin + len(coeffs)
        while True:
            if self.index == end:
                return np.dot(coeffs, self.buff)

            self.buff[:-1] = self.buff[1:]
            self.buff[-1] = self.src.next()  # throws StopIteration
            self.index += 1

def clip(x, lims):
    return min(max(x, lims[0]), lims[1])
