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


def equalize(signal, symbols, order):
    Nsym = config.Nsym
    Nfreq = config.Nfreq
    carriers = modem.carriers

    assert symbols.shape[1] == Nfreq
    length = symbols.shape[0]

    matched = np.array(carriers) / (0.5*Nsym)
    matched = matched[:, ::-1].transpose().conj()
    y = dsp.lfilter(x=signal, b=matched, a=[1])

    A = np.zeros([symbols.size, order], dtype=np.complex128)
    b = np.zeros([symbols.size], dtype=np.complex128)

    index = 0
    for j in range(Nfreq):
        for i in range(length):
            offset = (i+1)*Nsym
            row = y[offset-order:offset, j]
            A[index, :] = row
            b[index] = symbols[i, j]
            index += 1

    A = np.array(A)
    b = np.array(b)
    h, residuals, rank, sv = lstsq(A, b)
    h = h[::-1].real

    return h
