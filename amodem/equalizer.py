import numpy as np
from numpy.linalg import lstsq

from amodem import dsp
from amodem import config
from amodem import sampling

import itertools
import random

_constellation = [1, 1j, -1, -1j]
modem = dsp.MODEM(config)


def train_symbols(length, seed=0, Nfreq=config.Nfreq):
    r = random.Random(seed)
    choose = lambda: [r.choice(_constellation) for j in range(Nfreq)]
    return np.array([choose() for i in range(length)])


def modulator(symbols, carriers=modem.carriers):
    gain = 1.0 / len(carriers)
    result = []
    for s in symbols:
        result.append(np.dot(s, carriers))
    result = np.concatenate(result).real * gain
    assert np.max(np.abs(result)) <= 1
    return result


def demodulator(signal, size):
    signal = itertools.chain(signal, itertools.repeat(0))
    symbols = dsp.Demux(sampling.Sampler(signal), config.frequencies)
    return np.array(list(itertools.islice(symbols, size)))


def equalize_symbols(signal, symbols, order, lookahead=0):
    Nsym = config.Nsym
    Nfreq = config.Nfreq
    carriers = modem.carriers

    assert symbols.shape[1] == Nfreq
    length = symbols.shape[0]

    matched = np.array(carriers) / (0.5*Nsym)
    matched = matched[:, ::-1].transpose().conj()
    signal = np.concatenate([signal, np.zeros(lookahead)])
    y = dsp.lfilter(x=signal, b=matched, a=[1])

    A = []
    b = []

    for j in range(Nfreq):
        for i in range(length):
            offset = (i+1)*Nsym
            row = y[offset-order:offset+lookahead, j]
            A.append(row)
            b.append(symbols[i, j])

    A = np.array(A)
    b = np.array(b)
    h, residuals, rank, sv = lstsq(A, b)
    h = h[::-1].real

    return h


def equalize_signal(signal, expected, order, lookahead=0):
    signal = np.concatenate([np.zeros(order-1), signal, np.zeros(lookahead)])
    length = len(expected)

    A = []
    b = []

    for i in range(length - order):
        offset = order + i
        row = signal[offset-order:offset+lookahead]
        A.append(np.array(row, ndmin=2))
        b.append(expected[i])

    A = np.concatenate(A, axis=0)
    b = np.array(b)
    h, residuals, rank, sv = lstsq(A, b)
    h = h[::-1].real
    return h
