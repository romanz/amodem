import numpy as np
from numpy import linalg

import common

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
    def __init__(self, symbols):
        self._enc = {}
        symbols = np.array(list(symbols))
        bits_per_symbol = np.log2(len(symbols))
        bits_per_symbol = np.round(bits_per_symbol)
        N = (2 ** bits_per_symbol)
        assert N == len(symbols)
        bits_per_symbol = int(bits_per_symbol)

        for i, v in enumerate(symbols):
            bits = tuple(int(i & (1 << j) != 0) for j in range(bits_per_symbol))
            self._enc[bits] = v

        self._dec = {v: k for k, v in self._enc.items()}
        self.symbols = symbols
        self.bits_per_symbol = bits_per_symbol

    def encode(self, bits):
        trailing_bits = len(bits) % self.bits_per_symbol
        if trailing_bits:
            bits = bits + [0] * (self.bits_per_symbol - trailing_bits)
        for i in range(0, len(bits), self.bits_per_symbol):
            bits_tuple = tuple(bits[i:i+self.bits_per_symbol])
            s = self._enc[bits_tuple]
            yield s

    def decode(self, symbols):
        for s in symbols:
            index = np.argmin(np.abs(s - self.symbols))
            S = self.symbols[index]
            yield self._dec[S]

modulator = QAM(common.symbols)

modem_bps = common.baud * modulator.bits_per_symbol * len(common.frequencies)


def clip(x, lims):
    return min(max(x, lims[0]), lims[1])


def power(x):
    return np.dot(x.conj(), x).real / len(x)


def exp_iwt(freq, n):
    iwt = 2j * np.pi * freq * np.arange(n) * common.Ts
    return np.exp(iwt)


def norm(x):
    return np.sqrt(np.dot(x.conj(), x).real)


def coherence(x, freq):
    n = len(x)
    Hc = exp_iwt(-freq, n) / np.sqrt(0.5*n)
    return np.dot(Hc, x) / norm(x)


def extract_symbols(x, freq, offset=0):
    Hc = exp_iwt(-freq, common.Nsym) / (0.5*common.Nsym)
    func = lambda y: np.dot(Hc, y)

    iterator = common.iterate(x, common.Nsym, advance=common.Nsym, func=func)
    for _, symbol in iterator:
        yield symbol


def drift(S):
    x = np.arange(len(S))
    x = x - np.mean(x)
    y = np.unwrap(np.angle(S)) / (2*np.pi)
    y = y - np.mean(y)
    a = np.dot(x, y) / np.dot(x, x)
    return a
