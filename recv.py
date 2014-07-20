#!/usr/bin/env python
import numpy as np
import logging
import itertools
import time
import sys
import os

log = logging.getLogger(__name__)

import sigproc
import loop
import train
from common import *

if os.environ.get('PYLAB') == '1':
    import pylab
    import show
    WIDTH = np.floor(np.sqrt(len(frequencies)))
    HEIGHT = np.ceil(len(frequencies) / float(WIDTH))
else:
    pylab = None

COHERENCE_THRESHOLD = 0.95

CARRIER_DURATION = sum(train.prefix)
CARRIER_THRESHOLD = int(0.95 * CARRIER_DURATION)


def detect(x, freq):
    counter = 0
    for offset, buf in iterate(x, Nsym):
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


def take(symbols, n):
    symbols = itertools.islice(symbols, n)
    return np.array(list(symbols))


def receive_prefix(symbols):
    S = take(symbols, len(train.prefix))[:, carrier_index]
    y = np.abs(S)
    bits = np.round(y)

    bits = np.array(bits, dtype=int)
    if all(bits != train.prefix):
        raise ValueError('Incorrect prefix')

    log.info('Prefix OK')

    pilot_tone = S[np.array(train.prefix, dtype=bool)]
    err = sigproc.drift(pilot_tone) / (Tsym * Fc)
    log.info('Frequency error: %.2f ppm', err * 1e6)
    return err


def train_receiver(symbols, freqs):
    filters = {}
    scaling_factor = len(freqs)  # to avoid saturation
    training = np.array(train.equalizer)
    if pylab:
        pylab.figure()

    symbols = take(symbols, len(training) * len(freqs))
    for i, freq in enumerate(freqs):
        size = len(training)
        offset = i * size
        S = symbols[offset:offset+size, i]

        filt = sigproc.train(S, training * scaling_factor)
        filters[freq] = filt

        S = list(filt(S))
        y = np.array(S) / scaling_factor
        if pylab:
            pylab.subplot(HEIGHT, WIDTH, i+1)
            show.constellation(y, 'Train: $F_c = {}Hz$'.format(freq))

        train_result = np.round(y)
        if not all(train_result == training):
            raise ValueError('#{} training failed on {} Hz'.format(i, freq))

        noise = y - training
        Pnoise = sigproc.power(noise)
        log.info('%10.1f kHz: Noise sigma=%.4f, SNR=%.1f dB',
                 freq/1e3, Pnoise**0.5, 10*np.log10(1/Pnoise))

    return filters


stats = {}


def demodulate(symbols, filters, freqs):
    streams = []
    symbol_list = []
    errors = {}

    def error_handler(received, decoded, freq):
        errlist = errors.setdefault(freq, [])
        errlist.append(received - decoded)

    generators = split(symbols, n=len(freqs))
    for freq, S in zip(freqs, generators):
        S = filters[freq](S)

        if pylab:
            equalized = []
            S = icapture(S, result=equalized)
            symbol_list.append(equalized)

        freq_handler = functools.partial(error_handler, freq=freq)
        bits = sigproc.modulator.decode(S, freq_handler)  # list of bit tuples
        streams.append(bits)  # stream per frequency

    stats['symbol_list'] = symbol_list
    stats['rx_bits'] = 0
    stats['rx_start'] = time.time()

    log.info('Demodulation started')
    for block in itertools.izip(*streams):  # block per frequency
        for bits in block:
            stats['rx_bits'] = stats['rx_bits'] + len(bits)
            yield bits


def receive(signal, freqs):
    signal = loop.FreqLoop(signal, freqs)
    symbols = iter(signal)

    err = receive_prefix(symbols)
    signal.sampler.freq -= err

    filters = train_receiver(symbols, freqs)
    data_bits = demodulate(symbols, filters, freqs)
    return itertools.chain.from_iterable(data_bits)


def decode(bits_iterator):
    import bitarray
    import ecc

    def blocks():
        while True:
            bits = itertools.islice(bits_iterator, 8 * ecc.BLOCK_SIZE)
            block = bitarray.bitarray(endian='little')
            block.extend(bits)
            if not block:
                break
            yield bytearray(block.tobytes())

    return ecc.decode(blocks())


def main(fname):

    log.info('Running MODEM @ {:.1f} kbps'.format(sigproc.modem_bps / 1e3))

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
    log.info('Carrier detected at ~%.1f ms @ %.1f kHz:'
             ' coherence=%.3f%%, amplitude=%.3f',
             begin * Tsym * 1e3 / Nsym, Fc / 1e3,
             np.abs(sigproc.coherence(x_, Fc)) * 100, amp)

    start = find_start(x, begin)
    x = x[start:]
    peak = np.max(np.abs(x))
    if peak > SATURATION_THRESHOLD:
        raise ValueError('Saturation detected: {:.3f}'.format(peak))

    size = 0
    bits = receive(x / amp, frequencies)
    for chunk in decode(bits):
        sys.stdout.write(chunk)
        size = size + len(chunk)

    log.info('Decoded %.3f kB', size / 1e3)

    duration = time.time() - stats['rx_start']
    audio_time = stats['rx_bits'] / sigproc.modem_bps
    log.info('Demodulated %.3f kB @ %.3f seconds = %.1f%% realtime',
             stats['rx_bits'] / 8e3, duration, 100 * duration / audio_time)

    if pylab:
        pylab.figure()
        symbol_list = np.array(symbol_list)
        for i, freq in enumerate(freqs):
            pylab.subplot(HEIGHT, WIDTH, i+1)
            show.constellation(symbol_list[i], '$F_c = {} Hz$'.format(freq))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)-12s %(message)s')

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('fname')
    args = p.parse_args()
    try:
        main(fname=args.fname)
    except Exception as e:
        log.exception(e)
    finally:
        if pylab:
            pylab.show()
