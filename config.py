import numpy as np

Fs = 32e3
Ts = 1.0 / Fs

frequencies = (1 + np.arange(8)) * 1e3
carrier_index = 0
Fc = frequencies[carrier_index]
Tc = 1.0 / Fc

symbols = np.array([complex(x, y)
                   for x in np.linspace(-1, 1, 8)
                   for y in np.linspace(-1, 1, 8)]) / np.sqrt(2)

Tsym = 1e-3
Nsym = int(Tsym / Ts)
baud = int(1/Tsym)
