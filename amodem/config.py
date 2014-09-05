Fs = 32000.0  # sampling frequency [Hz]
Tsym = 0.001  # symbol duration [seconds]
Nfreq = 8     # number of frequencies used
Nx = 8
Ny = 8
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

assert Nx == 2 ** round(np.log2(Nx))
assert Ny == 2 ** round(np.log2(Ny))

xs = np.linspace(-1, 1, Nx) if Nx > 1 else [0.0]
ys = np.linspace(-1, 1, Ny) if Ny > 1 else [0.0]
symbols = np.array([complex(x, y) for x in xs for y in ys])
symbols = symbols / np.max(np.abs(symbols))

Nsym = int(Tsym / Ts)
baud = int(1/Tsym)
