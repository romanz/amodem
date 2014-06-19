import hashlib
import struct
import logging
log = logging.getLogger(__name__)

Fs = 32e3
Ts = 1.0 / Fs

Fc = 9e3
Tc = 1.0 / Fc

Tsym = 1e-3
Nsym = int(Tsym / Fs)

F0 = Fc - 1e3
F1 = Fc + 1e3
Nsym = int(Tsym / Ts)
baud = int(1/Tsym)

scaling = 10000.0

LENGTH_FORMAT = '<I'

def pack(data):
    log.info('Sending {} bytes, checksum: {}'.format(len(data), checksum(data)))
    data = struct.pack(LENGTH_FORMAT, len(data)) + data
    return data


def unpack(data):
    length_size = struct.calcsize(LENGTH_FORMAT)
    length, data = data[:length_size], data[length_size:]
    length, = struct.unpack(LENGTH_FORMAT, length)
    data = data[:length]
    log.info('Decoded {} bytes, leftover: {}, checksum: {}'.format(len(data), len(data)-length, checksum(data)))
    return data

def checksum(data):
    return '\033[0;32m{}\033[0m'.format(hashlib.sha256(data).hexdigest())


def to_bits(chars):
    for c in chars:
        val = ord(c)
        for i in range(8):
            mask = 1 << i
            yield (1 if (val & mask) else 0)


def to_bytes(bits):
    assert len(bits) == 8
    byte = sum(b << i for i, b in enumerate(bits))
    return chr(byte)

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
    plot(F0)
    plot(F1)
    pylab.show()
