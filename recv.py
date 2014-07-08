import numpy as np
import os
if os.environ.get('PYLAB') is not None:
    import pylab
    import show
else:
    pylab = None

import logging
import itertools
log = logging.getLogger(__name__)

import sigproc
import loop
import train
from common import *

COHERENCE_THRESHOLD = 0.95

CARRIER_DURATION = sum(train.prefix)
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

def take(symbols, i, n):
    return np.array([s if i is None else s[i] for s in itertools.islice(symbols, n)])

def receive(x, freqs):
    x = list(x)
    lp = loop.FreqLoop(x, freqs, prefix=0.0)

    symbols = iter(lp)

    S = take(symbols, carrier_index, len(train.prefix))
    y = np.abs(S)
    bits = np.round(y)

    bits = np.array(bits, dtype=int)
    if all(bits != train.prefix):
        return None
    log.info('Prefix OK')

    err = sigproc.drift( S[np.array(train.prefix, dtype=bool)] ) / (Tsym * Fc)
    log.info('Frequency error: %.2f ppm', err * 1e6)
    lp.sampler.freq -= err

    filters = {}

    full_scale = len(freqs)
    training_bits = np.array(train.equalizer)
    expected = full_scale * training_bits
    if pylab:
        pylab.figure()
        width = np.floor(np.sqrt(len(freqs)))
        height = np.ceil(len(freqs) / float(width))

    for i, freq in enumerate(freqs):
        S = take(symbols, i, len(expected))

        filt = sigproc.train(S, expected)
        filters[freq] = filt

        S = filt(S)
        y = np.array(list(S)).real
        if pylab:
            pylab.subplot(height, width, i+1)
            pylab.plot(y, '-', expected, '-')
            pylab.title('Train: $F_c = {}Hz$'.format(freq))

        train_result = y > 0.5 * full_scale
        if not all(train_result == training_bits):
            return None

        noise = y - expected
        Pnoise = sigproc.power(noise)
        log.info('{:10.1f} kHz: Noise sigma={:.4f}, SNR={:.1f} dB'.format( freq/1e3, Pnoise**0.5, 10*np.log10(1/Pnoise) ))

    streams = []
    ugly_hack = itertools.izip(*list(symbols))
    i = 0
    if pylab:
        pylab.figure()

    for freq, S in zip(freqs, ugly_hack):
        i += 1
        S = filters[freq](S)
        S = np.array(list(S))
        if pylab:
            pylab.subplot(height, width, i)
            show.constellation(S, title='$F_c = {} Hz$'.format(freq))
        bits = sigproc.modulator.decode(S)  # list of bit tuples
        streams.append(bits)

    bitstream = []
    for block in itertools.izip(*streams):
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
        data = iterate(data_bits, bufsize=8, advance=8, func=to_byte)
        data = ''.join(c for _, c in data)
        log.info('Demodulated %.3f kB', len(data) / 1e3)
        import ecc
        data = ecc.decode(data)
        if data is None:
            log.warning('No blocks decoded!')
            return

        log.info('Decoded %.3f kB', len(data) / 1e3)
        with file('data.recv', 'wb') as f:
            f.write(data)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-12s %(message)s')
    main('rx.int16')
    if pylab:
        pylab.show()
