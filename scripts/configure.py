#!/usr/bin/env python
template = '''import numpy as np

## Parameters
Fs = {Fs}  # sampling frequency [Hz]
Nfreq = {Nfreq}  # number of frequencies used
Tsym = {Tsym}  # symbol duration [seconds]
Nx = {Nx}
Ny = {Ny}

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
'''

defaults = dict(Fs=32e3, Nx=8, Ny=8, Tsym=1e-3, Nfreq=8)

import sys
args = sys.argv[1:]
for arg in args:
    name, value = arg.split('=')
    if name in defaults:
        T = type(defaults[name])
        defaults[name] = T(value)

content = template.format(**defaults)
sys.stdout.write(content)
