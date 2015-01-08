import numpy as np


class Configuration(object):
    Fs = 32000.0  # sampling frequency [Hz]
    Tsym = 0.001  # symbol duration [seconds]
    Nfreq = 8     # number of frequencies used
    Npoints = 64
    F0 = 1e3

    # audio config
    bits_per_sample = 16
    sample_size = bits_per_sample // 8
    samples_per_buffer = 4096

    # sender config
    silence_start = 1.0
    silence_stop = 1.0

    # receiver config
    skip_start = 0.1

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

        self.Ts = 1.0 / self.Fs
        self.Fsym = 1 / self.Tsym
        self.frequencies = self.F0 + np.arange(self.Nfreq) * self.Fsym
        self.carrier_index = 0
        self.Fc = self.frequencies[self.carrier_index]

        self.Nsym = int(self.Tsym / self.Ts)
        self.baud = int(1.0 / self.Tsym)

        bits_per_symbol = np.log2(self.Npoints)
        assert int(bits_per_symbol) == bits_per_symbol
        self.bits_per_baud = bits_per_symbol * self.Nfreq
        self.modem_bps = self.baud * self.bits_per_baud
        self.carriers = np.array([
            np.exp(2j * np.pi * f * np.arange(0, self.Nsym) * self.Ts)
            for f in self.frequencies
        ])

        # QAM constellation
        Nx = 2 ** int(np.ceil(bits_per_symbol / 2))
        Ny = self.Npoints // Nx
        symbols = [complex(x, y) for x in range(Nx) for y in range(Ny)]
        symbols = np.array(symbols)
        symbols = symbols - symbols[-1]/2
        self.symbols = symbols / np.max(np.abs(symbols))

# MODEM configurations for various bitrates [kbps]
bitrates = {
    1: Configuration(F0=8e3, Npoints=2, Nfreq=1),
    2: Configuration(F0=8e3, Npoints=4, Nfreq=1),
    4: Configuration(F0=8e3, Npoints=16, Nfreq=1),
    8: Configuration(F0=8e3, Npoints=16, Nfreq=2),
    16: Configuration(F0=6e3, Npoints=16, Nfreq=4),
    32: Configuration(F0=3e3, Npoints=16, Nfreq=8),
    48: Configuration(F0=3e3, Npoints=64, Nfreq=8),
    54: Configuration(F0=3e3, Npoints=64, Nfreq=9),
    60: Configuration(F0=2e3, Npoints=64, Nfreq=10),
}

fastest = lambda: bitrates[max(bitrates)]
slowest = lambda: bitrates[min(bitrates)]
