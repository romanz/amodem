import numpy as np
import pylab

import logging
import functools
import itertools
logging.basicConfig(level=0, format='%(message)s')
log = logging.getLogger(__name__)

import sigproc
import show
from common import *

COHERENCE_THRESHOLD = 0.95

CARRIER_DURATION = 300
CARRIER_THRESHOLD = int(0.95 * CARRIER_DURATION)

def detect(x, freq):
    counter = 0
    for offset, buf in iterate(x, Nsym, advance=Nsym):
        coeff = sigproc.coherence(buf, Fc)
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

    Hc = sigproc.exp_iwt(Fc, len(x_))
    P = np.abs(Hc.conj() * x_) ** 2
    cumsumP = P.cumsum()
    start = begin + np.argmax(cumsumP[length:] - cumsumP[:-length])
    log.info('Carrier starts at {:.3f} ms'.format(start * Tsym * 1e3 / Nsym))
    return start

def extract_symbols(x, freq, offset=0):
    Hc = sigproc.exp_iwt(-freq, Nsym) / (0.5*Nsym)
    func = lambda y: np.dot(Hc, y)
    for _, symbol in iterate(x, Nsym, advance=Nsym, func=func):
        yield symbol

def demodulate(x, freq, filt, plot=None):
    S = extract_symbols(x, freq) # samples -> symbols
    S = np.array(list(filt(S)))  # apply equalizer
    if plot:
        plot()
        show.constellation(S, title='$F_c = {} kHz$'.format(freq / 1e3))
    for bits in sigproc.modulator.decode(S):  # list of bit tuples
        yield bits

def receive(x, freqs):
    prefix = [1]*300 + [0]*100
    symbols = itertools.islice(extract_symbols(x, Fc), len(prefix))
    bits = np.round(np.abs(list(symbols)))
    bits = np.array(bits, dtype=int)
    if all(bits[:len(prefix)] != prefix):
        return None

    log.info( 'Prefix OK')
    x = x[len(prefix)*Nsym:]
    filters = {}
    for freq in freqs:
        training = ([1]*10 + [0]*10)*20 + [0]*100
        S = list(itertools.islice(extract_symbols(x, freq), len(training)))

        filt = sigproc.train(S, training)
        filters[freq] = filt

        S = list(filt(S))
        y = np.array(S).real

        train_result = y > 0.5
        if not all(train_result == np.array(training)):
            pylab.plot(y, '-', training, '-')
            return None

        noise = y - train_result
        Pnoise = sigproc.power(noise)
        log.debug('{:10.1f}Hz: Noise sigma={:.4f}, SNR={:.1f} dB'.format( freq, Pnoise**0.5, 10*np.log10(1/Pnoise) ))

        x = x[len(training)*Nsym:]

    results = []
    sz = int(np.ceil(np.sqrt(len(freqs))))
    for i, freq in enumerate(freqs):
        plot = functools.partial(pylab.subplot, sz, sz, i+1)
        results.append( demodulate(x * len(freqs), freq, filters[freq], plot=plot) )

    bitstream = []
    for block in itertools.izip(*results):
        for bits in block:
            bitstream.extend(bits)

    return bitstream


def main(fname):

    _, x = load(open(fname, 'rb'))
    result = detect(x, Fc)
    if result is None:
        log.info('No carrier detected')
        return

    begin, end = result
    x_ = x[begin:end]
    Hc = sigproc.exp_iwt(-Fc, len(x_))
    Zc = np.dot(Hc, x_) / (0.5*len(x_))
    amp = abs(Zc)
    log.info('Carrier detected at ~{:.1f} ms @ {:.1f} kHz: coherence={:.3f}%, amplitude={:.3f}'.format(
          begin * Tsym * 1e3 / Nsym, Fc / 1e3, abs(sigproc.coherence(x_, Fc)) * 100, amp
    ))

    start = find_start(x, begin)
    x = x[start:]
    peak = np.max(np.abs(x))
    if peak > SATURATION_THRESHOLD:
        raise ValueError('Saturation detected: {:.3f}'.format(peak))

    data_bits = receive(x / amp, frequencies)
    if data_bits is None:
        log.info('Cannot demodulate symbols!')
    else:
        import ecc
        data = iterate(data_bits, bufsize=8, advance=8, func=to_byte)
        data = ''.join(c for _, c in data)
        data = ecc.decode(data)
        with file('data.recv', 'wb') as f:
            f.write(data)

if __name__ == '__main__':
    main('rx_.int16')
    import os
    if os.environ.get('SHOW') is not None:
        pylab.show()
