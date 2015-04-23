from . import dsp
from . import sampling
from . import levinson

import numpy as np
import itertools


class Equalizer(object):

    def __init__(self, config):
        self.carriers = config.carriers
        self.omegas = 2 * np.pi * np.array(config.frequencies) / config.Fs
        self.Nfreq = config.Nfreq
        self.Nsym = config.Nsym

    def train_symbols(self, length, constant_prefix=16):
        r = dsp.prbs(reg=1, poly=0x1100b, bits=2)
        constellation = [1, 1j, -1, -1j]

        symbols = []
        for _ in range(length):
            symbols.append([constellation[next(r)] for _ in range(self.Nfreq)])

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


prefix = [1]*200 + [0]*50
equalizer_length = 200
silence_length = 50


def train(signal, expected, order, lookahead=0):
    padding = np.zeros(lookahead)
    assert len(signal) == len(expected)
    x = np.concatenate([signal, padding])
    y = np.concatenate([padding, expected])

    N = order + lookahead  # filter length
    Rxx = np.zeros(N)
    Rxy = np.zeros(N)
    for i in range(N):
        Rxx[i] = np.dot(x[i:], x[:len(x)-i])
        Rxy[i] = np.dot(y[i:], x[:len(x)-i])
    return levinson.solver(t=Rxx, y=Rxy)
