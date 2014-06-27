import cStringIO
import numpy as np

import logging
log = logging.getLogger(__name__)

Fs = 32e3
Ts = 1.0 / Fs

frequencies = (np.arange(4) + 8) * 1e3
carrier_index = len(frequencies)/2
Fc = frequencies[carrier_index]
Tc = 1.0 / Fc

Tsym = 1e-3
Nsym = int(Tsym / Ts)
baud = int(1/Tsym)

scaling = 32000.0  # out of 2**15
SATURATION_THRESHOLD = 1.0

LENGTH_FORMAT = '<I'

def to_bits(bytes_list):
    for val in bytes_list:
        for i in range(8):
            mask = 1 << i
            yield (1 if (val & mask) else 0)


def to_bytes(bits):
    assert len(bits) == 8
    byte = sum(b << i for i, b in enumerate(bits))
    return chr(byte)

def load(fname):
    data = open(fname, 'rb').read()
    return loads(data)

def loads(data):
    x = np.fromstring(data, dtype='int16')
    x = x / scaling
    t = np.arange(len(x)) / Fs
    return t, x

def dumps(sym, n=1):
    sym = sym.imag * scaling
    sym = sym.astype('int16')
    data = sym.tostring()
    return data * n

def norm(x):
    return np.sqrt(np.dot(x.conj(), x).real)

if __name__ == '__main__':

    import pylab
    def plot(f):
        t = pylab.linspace(0, Tsym, 1e3)
        x = pylab.sin(2 * pylab.pi * f * t)
        pylab.plot(t / Tsym, x)
        t = pylab.linspace(0, Tsym, Nsym + 1)
        x = pylab.sin(2 * pylab.pi * f * t)
        pylab.plot(t / Tsym, x, '.k')

    plot(Fc)
    pylab.show()
