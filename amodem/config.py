Fs = 32000.0  # sampling frequency [Hz]
Tsym = 0.001  # symbol duration [seconds]
Nfreq = 8     # number of frequencies used
Npoints = 64
F0 = 1e3

# Update default configuration from environment variables
settings = {k: v for k, v in locals().items() if not k.startswith('_')}

import os
for k in settings.keys():
    v = settings[k]
    settings[k] = type(v)(os.environ.get(k, v))
locals().update(settings)

import numpy as np

Ts = 1.0 / Fs
Fsym = 1 / Tsym
frequencies = F0 + np.arange(Nfreq) * Fsym
carrier_index = 0
Fc = frequencies[carrier_index]
Tc = 1.0 / Fc

# Hexagonal symbol constellation (optimal "sphere packing")
I = np.arange(-Npoints, Npoints+1)
imag_factor = np.exp(1j * np.pi / 3.0)
offset = 0.5
symbols = [(x + y*imag_factor + offset) for x in I for y in I]
symbols.sort(key=lambda z: (z*z.conjugate()).real)
symbols = np.array(symbols[:Npoints])
symbols = symbols / np.max(np.abs(symbols))

Nsym = int(Tsym / Ts)
baud = int(1/Tsym)
