"""Configuration class."""

import numpy as np


class Configuration:
    Fs = 32000.0  # sampling frequency [Hz]
    Tsym = 0.001  # symbol duration [seconds]
    Npoints = 64
    frequencies = [1e3, 8e3]  # use 1..8 kHz carriers
    negotiate_frequencies = [12e3]  # negotiate carrier

    # audio config
    bits_per_sample = 16
    latency = 0.1

    # sender config
    silence_start = 0.5
    silence_stop = 0.5

    # receiver config
    skip_start = 0.1
    timeout = 60.0

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

        self.sample_size = self.bits_per_sample // 8
        assert self.sample_size * 8 == self.bits_per_sample

        self.Ts = 1.0 / self.Fs
        self.Fsym = 1 / self.Tsym
        self.Nsym = int(self.Tsym / self.Ts)
        self.baud = int(1.0 / self.Tsym)
        assert self.baud * self.Tsym == 1

        if len(self.frequencies) != 1:
            first, last = self.frequencies
            self.frequencies = np.arange(first, last + self.baud, self.baud)

        self.Nfreq = len(self.frequencies)
        self.carrier_index = 0
        self.Fc = self.frequencies[self.carrier_index]

        bits_per_symbol = int(np.log2(self.Npoints))
        assert 2 ** bits_per_symbol == self.Npoints
        self.bits_per_baud = bits_per_symbol * self.Nfreq
        self.modem_bps = self.baud * self.bits_per_baud
        self.carriers = np.array([
            np.exp(2j * np.pi * f * np.arange(0, self.Nsym) * self.Ts)
            for f in self.frequencies
        ])

        # QAM constellation
        Nx = 2 ** int(np.ceil(bits_per_symbol // 2))
        Ny = self.Npoints // Nx
        symbols = [complex(x, y) for x in range(Nx) for y in range(Ny)]
        symbols = np.array(symbols)
        symbols = symbols - symbols[-1]/2
        self.symbols = symbols / np.max(np.abs(symbols))


# MODEM configurations for various bitrates [kbps]
bitrates = {
    1: Configuration(Fs=8e3, Npoints=2, frequencies=[2e3]),
    2: Configuration(Fs=8e3, Npoints=4, frequencies=[2e3]),
    4: Configuration(Fs=8e3, Npoints=16, frequencies=[2e3]),
    8: Configuration(Fs=8e3, Npoints=16, frequencies=[1e3, 2e3]),
    12: Configuration(Fs=16e3, Npoints=16, frequencies=[3e3, 5e3]),
    16: Configuration(Fs=16e3, Npoints=16, frequencies=[2e3, 5e3]),
    20: Configuration(Fs=16e3, Npoints=16, frequencies=[2e3, 6e3]),
    24: Configuration(Fs=16e3, Npoints=16, frequencies=[1e3, 6e3]),
    28: Configuration(Fs=32e3, Npoints=16, frequencies=[3e3, 9e3]),
    32: Configuration(Fs=32e3, Npoints=16, frequencies=[2e3, 9e3]),
    40: Configuration(Fs=32e3, Npoints=16, frequencies=[2e3, 11e3]),
    36: Configuration(Fs=32e3, Npoints=64, frequencies=[4e3, 9e3]),
    42: Configuration(Fs=32e3, Npoints=64, frequencies=[4e3, 10e3]),
    48: Configuration(Fs=32e3, Npoints=64, frequencies=[3e3, 10e3]),
    54: Configuration(Fs=32e3, Npoints=64, frequencies=[2e3, 10e3]),
    60: Configuration(Fs=32e3, Npoints=64, frequencies=[2e3, 11e3]),
    64: Configuration(Fs=32e3, Npoints=256, frequencies=[3e3, 10e3]),
    72: Configuration(Fs=32e3, Npoints=256, frequencies=[2e3, 10e3]),
    80: Configuration(Fs=32e3, Npoints=256, frequencies=[2e3, 11e3]),
}


def fastest():
    return bitrates[max(bitrates)]


def slowest():
    return bitrates[min(bitrates)]
