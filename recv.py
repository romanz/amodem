import numpy as np
from numpy import linalg
import pylab

import sys
import struct
import logging
logging.basicConfig(level=0, format='%(message)s')
log = logging.getLogger(__name__)

import sigproc
from common import *

NFFT = 256
COHERENCE_THRESHOLD = 0.9

CARRIER_DURATION = 300
CARRIER_THRESHOLD = int(0.9 * CARRIER_DURATION)

def load(fname):
    x = np.fromfile(open(fname, 'rb'), dtype='int16') / scaling
    t = np.arange(len(x)) / Fs
    return t, x

def show(t, x):
    ax1 = pylab.subplot(211)
    pylab.plot(t, x)

    pylab.subplot(212, sharex=ax1)
    Pxx, freqs, bins, im = pylab.specgram(x,
        NFFT=NFFT, Fs=Fs, noverlap=NFFT/2, cmap=pylab.cm.gist_heat)

    pylab.show()

def norm(x):
    return np.sqrt(np.dot(x.conj(), x).real)

def test_coherence(t, x, f, start=None, end=None):
    if start is None:
        start = -np.inf
    if end is None:
        end = np.inf

    I = (start <= t) & (t < end)
    t = t[I]
    x = x[I]

    x = x / norm(x)
    ph = 2*np.pi*f*t
    cos = np.cos(ph); cos = cos / norm(cos)
    sin = np.sin(ph); sin = sin / norm(sin)
    coeff = np.dot(cos, x)**2 + np.dot(sin, x)**2
    log.info('{:5.1f} kHz: {:.1f}%'.format(f / 1e3, coeff * 100))

def test(t, x):
    test_coherence(t, x, f=Fc, start=0.1, end=0.11)
    test_coherence(t, x, f=F0, start=0.32, end=0.4)
    test_coherence(t, x, f=F1, start=0.42, end=0.5)

def iterate(x, bufsize, offset=0, advance=1, func=None):
    while True:
        buf = x[offset:offset+bufsize]
        if len(buf) == bufsize:
            result = func(buf) if func else buf
            yield offset, result
        else:
            return
        offset += advance

def exp_iwt(freq, n):
    iw = 2j * np.pi * freq
    t = np.arange(n) * Ts
    return np.exp(iw * t)

def coherence(x, freq):
    n = len(x)
    Hc = exp_iwt(freq, n) / np.sqrt(0.5*n)
    return np.dot(Hc, x) / norm(x)

def detect(freq):
    counter = 0
    for offset, coeff in iterate(x, Nsym, advance=Nsym, func=lambda x: coherence(x, Fc)):
        if abs(coeff) > COHERENCE_THRESHOLD:
            counter += 1
        else:
            counter = 0

        if counter == CARRIER_THRESHOLD:
            length = CARRIER_THRESHOLD * Nsym
            return offset - length + Nsym, offset

def find_start(x, start):
    WINDOW = Nsym * 10
    length = CARRIER_DURATION * Nsym
    begin, end = start - WINDOW, start + length + WINDOW
    x_ = x[begin:end]

    Hc = exp_iwt(Fc, len(x_))
    P = np.abs(Hc.conj() * x_) ** 2
    cumsumP = P.cumsum()
    start = np.argmax(cumsumP[length:] - cumsumP[:-length]) + begin
    log.info('Carrier starts at {:.3f} ms'.format(start * Tsym * 1e3 / Nsym))
    return start

def equalize(symbols):
    bits = np.round(np.abs(symbols))
    bits = np.array(bits, dtype=int)
    prefix = [1]*300 + [0]*100 + ([1]*10 + [0]*10)*20 + [0]*100
    n = len(prefix)
    if all(bits[:n] == prefix):

        S = symbols[:n]

        A = np.array([ S[1:], S[:-1], prefix[:-1] ]).T
        b = prefix[1:]

        b0, b1, a1 = linalg.lstsq(A, b)[0]
        y = np.array(list(sigproc.lfilter([b0, b1], [1, -a1], symbols)))
        constellation(y)

        prefix_bits, noise = slicer(y[:n], 0.5)
        assert(all(prefix_bits == np.array(prefix)))
        log.info( 'Prefix OK, at SNR: {:.1f} dB'.format( 20 * np.log10(np.sqrt(len(prefix_bits)) / norm(noise)) ) )

        data_bits = sigproc.qpsk.decode(y[n:])
        data_bits = list(data_bits)
        return data_bits

def slicer(symbols, threshold):
    bits = symbols.real > threshold
    noise = symbols - bits
    return bits, noise

def constellation(y):
    theta = np.linspace(0, 2*np.pi, 1000)

    pylab.figure()
    pylab.subplot(121)
    pylab.plot(y.real, y.imag, '.')
    pylab.plot(np.cos(theta), np.sin(theta), ':')
    keys = np.array(sigproc.qpsk._enc.values())
    print keys
    pylab.plot(keys.real, keys.imag, 'o')
    pylab.grid('on')
    pylab.axis('equal')
    pylab.axis(np.array([-1, 1, -1, 1]) * 1.1)

    pylab.subplot(122)
    pylab.plot(np.arange(len(y)) * Tsym, y.real, '.')
    pylab.grid('on')

def main(t, x):

    x = (x - np.mean(x))
    result = detect(Fc)
    if result is None:
        log.info('No carrier detected')
        return

    begin, end = result
    x_ = x[begin:end]
    t_ = t[begin:end]
    Hc = exp_iwt(-Fc, len(x_))
    Zc = np.dot(Hc, x_) / (0.5*len(x_))
    amp = abs(Zc)
    phase = np.angle(Zc, deg=True)
    log.info('Carrier detected at ~{:.1f} ms @ {:.1f} kHz: coherence={:.3f}%, amplitude={:.3f}'.format(
          begin * Tsym * 1e3 / Nsym, Fc / 1e3, abs(coherence(x_, Fc)) * 100, amp
    ))

    start = find_start(x, begin)
    x = x[start:] / amp
    t = t[start:]

    Hc = exp_iwt(-Fc, Nsym) / (0.5*Nsym)
    func = lambda y: np.dot(Hc, y)
    symbols = []
    for _, coeff in iterate(x, Nsym, advance=Nsym, func=func):
        symbols.append(coeff)
    symbols = np.array(symbols)

    data_bits = equalize(symbols)
    if data_bits is None:
        log.info('Cannot demodulate symbols!')
    else:
        data = iterate(data_bits, bufsize=8, advance=8, func=to_bytes)
        data = ''.join(c for _, c in data)
        log.info( 'Demodulated {} payload bydes'.format(len(data)) )
        data = unpack(data)
        log.info(repr(data))

    pylab.show()


if __name__ == '__main__':
    fname, = sys.argv[1:]
    t, x = load(fname)
    main(t, x)
    pylab.show()
