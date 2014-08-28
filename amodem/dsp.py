import numpy as np
from numpy import linalg
import logging

log = logging.getLogger(__name__)

from . import common
from .config import Ts, Nsym


class Filter(object):
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
    f = Filter(b=b, a=a)
    y = list(f(x))
    return np.array(y)


def estimate(x, y, order, lookahead=0):
    offset = order - 1
    assert offset >= lookahead
    b = y[offset-lookahead:len(x)-lookahead]

    A = []  # columns of x
    N = len(x) - order + 1
    for i in range(order):
        A.append(x[i:N+i])

    # switch to rows for least-squares
    h = linalg.lstsq(np.array(A).T, b)[0]
    return h[::-1]


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

        reals = np.array(list(sorted(set(symbols.real))))
        imags = np.array(list(sorted(set(symbols.imag))))
        self.real_factor = 1.0 / np.mean(np.diff(reals))
        self.imag_factor = 1.0 / np.mean(np.diff(imags))
        self.bias = reals[0] + 1j * imags[0]

        self.symbols_map = {}
        for S in symbols:
            s = S - self.bias
            real_index = round(s.real * self.real_factor)
            imag_index = round(s.imag * self.imag_factor)
            self.symbols_map[real_index, imag_index] = (S, self._dec[S])
        self.real_max = max(k[0] for k in self.symbols_map)
        self.imag_max = max(k[1] for k in self.symbols_map)

    def encode(self, bits):
        for _, bits_tuple in common.iterate(bits, self.bits_per_symbol, tuple):
            yield self._enc[bits_tuple]

    def decode(self, symbols, error_handler=None):
        real_factor = self.real_factor
        imag_factor = self.imag_factor
        real_max = self.real_max
        imag_max = self.imag_max
        bias = self.bias

        symbols_map = self.symbols_map
        for S in symbols:
            s = S - bias
            real_index = min(max(s.real * real_factor, 0), real_max)
            imag_index = min(max(s.imag * imag_factor, 0), imag_max)
            key = (round(real_index), round(imag_index))
            decoded_symbol, bits = symbols_map[key]
            if error_handler:
                error_handler(received=S, decoded=decoded_symbol)
            yield bits


class Demux(object):
    def __init__(self, sampler, freqs):
        self.sampler = sampler
        self.filters = [exp_iwt(-f, Nsym) / (0.5*Nsym) for f in freqs]
        self.filters = np.array(self.filters)

    def __iter__(self):
        return self

    def next(self):
        frame = self.sampler.take(size=Nsym)
        if len(frame) == Nsym:
            return np.dot(self.filters, frame)
        else:
            raise StopIteration

    __next__ = next


class MODEM(object):
    def __init__(self, config):
        self.qam = QAM(config.symbols)
        self.baud = config.baud
        self.freqs = config.frequencies
        self.bits_per_baud = self.qam.bits_per_symbol * len(self.freqs)
        self.modem_bps = self.baud * self.bits_per_baud
        self.carriers = np.array([
            np.exp(2j * np.pi * freq * np.arange(0, Nsym) * Ts)
            for freq in self.freqs
        ])


def exp_iwt(freq, n):
    iwt = 2j * np.pi * freq * np.arange(n) * Ts
    return np.exp(iwt)


def norm(x):
    return np.sqrt(np.dot(x.conj(), x).real)


def coherence(x, freq):
    n = len(x)
    Hc = exp_iwt(-freq, n) / np.sqrt(0.5*n)
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
