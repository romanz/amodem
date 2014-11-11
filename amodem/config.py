Fs = 32000.0  # sampling frequency [Hz]
Tsym = 0.001  # symbol duration [seconds]
Nfreq = 8     # number of frequencies used
Npoints = 64
F0 = 1e3

# Update default configuration from environment variables
settings = {k: v for k, v in locals().items() if not k.startswith('_')}

_prefix = 'AMODEM_'
import os
for k in settings.keys():
    v = settings[k]
    settings[k] = type(v)(os.environ.get(_prefix + k, v))
locals().update(settings)

import numpy as np

Ts = 1.0 / Fs
Fsym = 1 / Tsym
frequencies = F0 + np.arange(Nfreq) * Fsym
carrier_index = 0
Fc = frequencies[carrier_index]
Tc = 1.0 / Fc

Nsym = int(Tsym / Ts)
baud = int(1 / Tsym)

bits_per_symbol = np.log2(Npoints)
assert int(bits_per_symbol) == bits_per_symbol
bits_per_baud = bits_per_symbol * Nfreq
modem_bps = baud * bits_per_baud
carriers = np.array([
    np.exp(2j * np.pi * f * np.arange(0, Nsym) * Ts) for f in frequencies
])

# Hexagonal symbol constellation (optimal "sphere packing")
Nx = 2 ** int(np.ceil(bits_per_symbol / 2))
Ny = Npoints // Nx
symbols = np.array([complex(x, y) for x in range(Nx) for y in range(Ny)])
symbols = symbols - symbols[-1]/2
symbols = symbols / np.max(np.abs(symbols))
