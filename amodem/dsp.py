import numpy as np
from numpy import linalg
import logging

log = logging.getLogger(__name__)

from .config import Ts, Nsym
from .qam import QAM


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


def lfilter(b, a, x):
    f = IIR(b=b, a=a)
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

    def __repr__(self):
        return '<{:.3f} kbps, {:d}-QAM, {:d} carriers>'.format(
            self.modem_bps / 1e3, len(self.qam.symbols), len(self.carriers))

    __str__ = __repr__


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
