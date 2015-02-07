from . import dsp
from . import sampling

import numpy as np
from numpy.linalg import lstsq

import itertools
import random


class Equalizer(object):

    _constellation = [1, 1j, -1, -1j]

    def __init__(self, config):
        self.carriers = config.carriers
        self.omegas = 2 * np.pi * np.array(config.frequencies) / config.Fs
        self.Nfreq = config.Nfreq
        self.Nsym = config.Nsym

    def train_symbols(self, length, seed=0, constant_prefix=16):
        r = random.Random(seed)

        def random_symbol():
            ''' use low-level randomness for cross-version compatibility. '''
            return self._constellation[r.getrandbits(2)]

        symbols = []
        for _ in range(length):
            symbols.append([random_symbol() for _ in range(self.Nfreq)])

        symbols = np.array(symbols)
        # Constant symbols (for analog debugging)
        symbols[:constant_prefix, :] = 1
        return symbols

    def modulator(self, symbols):
        gain = 1.0 / len(self.carriers)
        result = []
        for s in symbols:
            result.append(np.dot(s, self.carriers))
        result = np.concatenate(result).real * gain
        assert np.max(np.abs(result)) <= 1
        return result

    def demodulator(self, signal, size):
        signal = itertools.chain(signal, itertools.repeat(0))
        symbols = dsp.Demux(sampler=sampling.Sampler(signal),
                            omegas=self.omegas, Nsym=self.Nsym)
        return np.array(list(itertools.islice(symbols, size)))


def train(signal, expected, order, lookahead=0):
    signal = [np.zeros(order-1), signal, np.zeros(lookahead)]
    signal = np.concatenate(signal)
    length = len(expected)

    A = []
    b = []
    # construct Ah=b over-constrained equation system,
    # used for least-squares estimation of the filter.
    for i in range(length - order):
        offset = order + i
        row = signal[offset-order:offset+lookahead]
        A.append(np.array(row, ndmin=2))
        b.append(expected[i])

    A = np.concatenate(A, axis=0)
    b = np.array(b)
    h = lstsq(A, b)[0]
    h = h[::-1].real
    return h


prefix = [1]*400 + [0]*50
equalizer_length = 500
silence_length = 100
