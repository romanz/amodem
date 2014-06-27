import numpy as np
import pylab

import logging
import itertools
logging.basicConfig(level=0, format='%(message)s')
log = logging.getLogger(__name__)

import sigproc
import ecc
from common import *

COHERENCE_THRESHOLD = 0.9

CARRIER_DURATION = 300
CARRIER_THRESHOLD = int(0.9 * CARRIER_DURATION)

def power(x):
    return np.dot(x.conj(), x).real / len(x)

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
    Hc = exp_iwt(-freq, n) / np.sqrt(0.5*n)
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

def extract_symbols(x, freq, offset=0):
    Hc = exp_iwt(-freq, Nsym) / (0.5*Nsym)
    func = lambda y: np.dot(Hc, y)
    for _, symbol in iterate(x, Nsym, advance=Nsym, func=func):
        yield symbol

def demodulate(x, freq, filt):
    S = extract_symbols(x, freq)
    S = np.array(list(filt.apply(S)))
    #constellation(S)
    for bits in sigproc.modulator.decode(S):  # list of bit tuples
        yield bits

def equalize(x, freqs):
    prefix = [1]*300 + [0]*100
    symbols = list(itertools.islice(extract_symbols(x, Fc), len(prefix)))
    bits = np.round(np.abs(symbols))
    bits = np.array(bits, dtype=int)
    if all(bits[:len(prefix)] != prefix):
        return None

    log.info( 'Prefix OK')
    x = x[len(prefix)*Nsym:]
    filters = {}
    for freq in freqs:
        training = ([1]*10 + [0]*10)*20 + [0]*100
        S = list(itertools.islice(extract_symbols(x, freq), len(training)))

        filt = sigproc.Filter.train(S, training)
        filters[freq] = filt

        S = list(filt.apply(S))
        y = np.array(S).real

        train_result = y > 0.5
        if not all(train_result == np.array(training)):
            pylab.plot(y, '-', training, '-')
            return None

        noise = y - train_result
        Pnoise = power(noise)
        log.debug('{:10.1f}Hz: Noise sigma={:.4f}, SNR={:.1f} dB'.format( freq, Pnoise**0.5, 10*np.log10(1/Pnoise) ))

        x = x[len(training)*Nsym:]

    results = []
    for freq in freqs:
        results.append( demodulate(x * len(freqs), freq, filters[freq]) )

    bitstream = []
    for block in itertools.izip(*results):
        for bits in block:
            bitstream.extend(bits)

    return bitstream


def constellation(y):
    theta = np.linspace(0, 2*np.pi, 1000)

    pylab.figure()
    pylab.subplot(121)
    pylab.plot(y.real, y.imag, '.')
    pylab.plot(np.cos(theta), np.sin(theta), ':')
    points = np.array(sigproc.modulator.points)
    pylab.plot(points.real, points.imag, 'o')
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
    Hc = exp_iwt(-Fc, len(x_))
    Zc = np.dot(Hc, x_) / (0.5*len(x_))
    amp = abs(Zc)
    log.info('Carrier detected at ~{:.1f} ms @ {:.1f} kHz: coherence={:.3f}%, amplitude={:.3f}'.format(
          begin * Tsym * 1e3 / Nsym, Fc / 1e3, abs(coherence(x_, Fc)) * 100, amp
    ))

    start = find_start(x, begin)
    x = x[start:]
    peak = np.max(np.abs(x))
    if peak > SATURATION_THRESHOLD:
        raise ValueError('Saturation detected: {:.3f}'.format(peak))

    data_bits = equalize(x / amp, frequencies)
    if data_bits is None:
        log.info('Cannot demodulate symbols!')
    else:
        data = iterate(data_bits, bufsize=8, advance=8, func=to_bytes)
        data = ''.join(c for _, c in data)
        data = ecc.decode(data)
        with file('data.recv', 'wb') as f:
            f.write(data)

if __name__ == '__main__':
    t, x = load('rx.int16')
    main(t, x)
    pylab.show()
