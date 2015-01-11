import numpy as np
from numpy import linalg

from . import common


class FIR(object):
    def __init__(self, h):
        self.h = np.array(h)
        self.x_state = [0] * len(self.h)

    def __call__(self, x):
        x_ = self.x_state
        h = self.h
        for v in x:
            x_ = [v] + x_[:-1]
            yield np.dot(x_, h)
        self.x_state = x_


class IIR(object):
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


class Demux(object):
    def __init__(self, sampler, omegas, Nsym):
        self.Nsym = Nsym
        self.filters = [exp_iwt(-w, Nsym) / (0.5*self.Nsym) for w in omegas]
        self.filters = np.array(self.filters)
        self.sampler = sampler

    def __iter__(self):
        return self

    def next(self):
        frame = self.sampler.take(size=self.Nsym)
        if len(frame) == self.Nsym:
            return np.dot(self.filters, frame)
        else:
            raise StopIteration

    __next__ = next


def exp_iwt(omega, n):
    return np.exp(1j * omega * np.arange(n))


def norm(x):
    return np.sqrt(np.dot(x.conj(), x).real)


def coherence(x, omega):
    n = len(x)
    Hc = exp_iwt(-omega, n) / np.sqrt(0.5*n)
    norm_x = norm(x)
    if norm_x:
        return np.dot(Hc, x) / norm_x
    else:
        return 0.0


def linear_regression(x, y):
    ''' Find (a,b) such that y = a*x + b. '''
    x = np.array(x)
    y = np.array(y)
    ones = np.ones(len(x))
    M = np.array([x, ones]).T
    a, b = linalg.lstsq(M, y)[0]
    return a, b


class MODEM(object):

    buf_size = 16

    def __init__(self, symbols):
        self.encode_map = {}
        symbols = np.array(list(symbols))
        bits_per_symbol = np.log2(len(symbols))
        bits_per_symbol = np.round(bits_per_symbol)
        N = (2 ** bits_per_symbol)
        assert N == len(symbols)
        bits_per_symbol = int(bits_per_symbol)

        for i, v in enumerate(symbols):
            bits = [int(i & (1 << j) != 0) for j in range(bits_per_symbol)]
            self.encode_map[tuple(bits)] = v

        self.symbols = symbols
        self.bits_per_symbol = bits_per_symbol

        bits_map = dict(item[::-1] for item in self.encode_map.items())
        self.decode_list = [(s, bits_map[s]) for s in self.symbols]

    def encode(self, bits):
        for bits_tuple in common.iterate(bits, self.bits_per_symbol, tuple):
            yield self.encode_map[bits_tuple]

    def decode(self, symbols, error_handler=None):
        ''' Maximum-likelihood decoding, using naive nearest-neighbour. '''
        symbols_vec = self.symbols
        _dec = self.decode_list
        for syms in common.iterate(symbols, self.buf_size, truncate=False):
            for received in syms:
                error = np.abs(symbols_vec - received)
                index = np.argmin(error)
                decoded, bits = _dec[index]
                if error_handler:
                    error_handler(received=received, decoded=decoded)
                yield bits
