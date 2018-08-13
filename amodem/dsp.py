"""Digital Signal Processing capabilities for amodem."""

import numpy as np

from . import common


class FIR:
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


class Demux:
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
        raise StopIteration

    __next__ = next


def exp_iwt(omega, n):
    return np.exp(1j * omega * np.arange(n))


def norm(x):
    return np.sqrt(np.dot(x.conj(), x).real)


def rms(x):
    return np.mean(np.abs(x) ** 2, axis=0) ** 0.5


def coherence(x, omega):
    n = len(x)
    Hc = exp_iwt(-omega, n) / np.sqrt(0.5*n)
    norm_x = norm(x)
    if not norm_x:
        return 0.0
    return np.dot(Hc, x) / norm_x


def linear_regression(x, y):
    """ Find (a,b) such that y = a*x + b. """
    x = np.array(x)
    y = np.array(y)
    mean_x = np.mean(x)
    mean_y = np.mean(y)
    x_ = x - mean_x
    y_ = y - mean_y
    a = np.dot(y_, x_) / np.dot(x_, x_)
    b = mean_y - a * mean_x
    return a, b


class MODEM:

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
        """ Maximum-likelihood decoding, using naive nearest-neighbour. """
        symbols_vec = self.symbols
        _dec = self.decode_list
        for received in symbols:
            error = np.abs(symbols_vec - received)
            index = np.argmin(error)
            decoded, bits = _dec[index]
            if error_handler:
                error_handler(received=received, decoded=decoded)
            yield bits


def prbs(reg, poly, bits):
    """ Simple pseudo-random number generator. """
    mask = (1 << bits) - 1

    size = 0  # effective register size (in bits)
    while (poly >> size) > 1:
        size += 1

    while True:
        yield reg & mask
        reg = reg << 1
        if reg >> size:
            reg = reg ^ poly
