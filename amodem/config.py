import numpy as np

## Parameters
Fs = 32000.0  # sampling frequency [Hz]
Nfreq = 8  # number of frequencies used
Tsym = 0.001  # symbol duration [seconds]
Nx = 8
Ny = 8

Ts = 1.0 / Fs

frequencies = (1 + np.arange(Nfreq)) * 1e3
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
