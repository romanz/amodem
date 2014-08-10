import numpy as np
import logging
import itertools
import functools
import collections
import time
import os

import bitarray

log = logging.getLogger(__name__)

from . import stream
from . import sigproc
from . import train
from . import common
from . import config
from . import ecc

modem = sigproc.MODEM(config)

if os.environ.get('PYLAB') == '1':
    import pylab
else:
    pylab = common.Dummy()

# Plots' size (WIDTH x HEIGHT)
HEIGHT = np.floor(np.sqrt(len(modem.freqs)))
WIDTH = np.ceil(len(modem.freqs) / float(HEIGHT))

COHERENCE_THRESHOLD = 0.95

CARRIER_DURATION = sum(train.prefix)
CARRIER_THRESHOLD = int(0.95 * CARRIER_DURATION)
SEARCH_WINDOW = 10  # symbols


def report_carrier(bufs, begin):
    x = np.concatenate(tuple(bufs)[-CARRIER_THRESHOLD:-1])
    Hc = sigproc.exp_iwt(-config.Fc, len(x))
    Zc = np.dot(Hc, x) / (0.5*len(x))
    amp = abs(Zc)
    log.info('Carrier detected at ~%.1f ms @ %.1f kHz:'
             ' coherence=%.3f%%, amplitude=%.3f',
             begin * config.Tsym * 1e3 / config.Nsym, config.Fc / 1e3,
             np.abs(sigproc.coherence(x, config.Fc)) * 100, amp)
    return amp


def detect(samples, freq):

    counter = 0
    bufs = collections.deque([], maxlen=config.baud)  # 1 second of symbols
    for offset, buf in common.iterate(samples, config.Nsym):
        bufs.append(buf)

        coeff = sigproc.coherence(buf, config.Fc)
        if abs(coeff) > COHERENCE_THRESHOLD:
            counter += 1
        else:
            counter = 0

        if counter == CARRIER_THRESHOLD:
            length = (CARRIER_THRESHOLD - 1) * config.Nsym
            begin = offset - length
            amplitude = report_carrier(bufs, begin=begin)
            break
    else:
        raise ValueError('No carrier detected')

    log.debug('Buffered %d ms of audio', len(bufs))

    to_append = SEARCH_WINDOW + (CARRIER_DURATION - CARRIER_THRESHOLD)
    bufs_iterator = common.iterate(samples, config.Nsym)
    for _, buf in itertools.islice(bufs_iterator, to_append):
        bufs.append(buf)

    bufs = tuple(bufs)[-CARRIER_DURATION-2*SEARCH_WINDOW:]
    buf = np.concatenate(bufs)

    offset = find_start(buf, length=config.Nsym*CARRIER_DURATION)
    start = begin - config.Nsym * SEARCH_WINDOW + offset
    log.info('Carrier starts at %.3f ms',
             start * config.Tsym * 1e3 / config.Nsym)

    return itertools.chain(buf[offset:], samples), amplitude


def find_start(buf, length):
    Hc = sigproc.exp_iwt(config.Fc, len(buf))
    P = np.abs(Hc.conj() * buf) ** 2
    cumsumP = P.cumsum()
    return np.argmax(cumsumP[length:] - cumsumP[:-length])


def receive_prefix(symbols):
    S = common.take(symbols, len(train.prefix))[:, config.carrier_index]
    sliced = np.round(S)
    pylab.figure()
    constellation(S, sliced, 'Prefix')

    bits = np.array(np.abs(sliced), dtype=int)
    if any(bits != train.prefix):
        raise ValueError('Incorrect prefix')

    log.info('Prefix OK')

    nonzeros = np.array(train.prefix, dtype=bool)
    pilot_tone = S[nonzeros]
    phase = np.unwrap(np.angle(pilot_tone)) / (2 * np.pi)
    indices = np.arange(len(phase))
    a, b = sigproc.linear_regression(indices, phase)

    freq_err = a / (config.Tsym * config.Fc)
    last_phase = a * indices[-1] + b
    log.debug('Current phase on carrier: %.3f', last_phase)

    expected_phase, = set(np.angle(sliced[nonzeros]) / (2 * np.pi))
    log.debug('Excepted phase on carrier: %.3f', expected_phase)

    sampling_err = (last_phase - expected_phase) * config.Nsym
    log.info('Frequency error: %.2f ppm', freq_err * 1e6)
    log.info('Sampling error: %.2f samples', sampling_err)
    return freq_err, sampling_err


def train_receiver(symbols, freqs):
    filters = {}
    scaling_factor = len(freqs)  # to avoid saturation
    training = np.array(train.equalizer)

    pylab.figure()
    symbols = common.take(symbols, len(training) * len(freqs))
    for i, freq in enumerate(freqs):
        size = len(training)
        offset = i * size
        S = symbols[offset:offset+size, i]

        filt = sigproc.train(S, training * scaling_factor)
        filters[freq] = filt

        Y = list(filt(S))
        y = np.array(Y) / scaling_factor

        pylab.subplot(HEIGHT, WIDTH, i+1)
        constellation(y, modem.qam.symbols,
                      'Train: $F_c = {}Hz$'.format(freq))
        pylab.plot(S.real, S.imag, '.-')

        train_result = np.round(y)
        if not all(train_result == training):
            raise ValueError('#{} training failed on {} Hz'.format(i, freq))

        noise = y - training
        Pnoise = sigproc.power(noise)
        log.info('%10.1f kHz: Noise sigma=%.4f, SNR=%.1f dB',
                 freq/1e3, Pnoise**0.5, 10*np.log10(1/Pnoise))

    return filters


stats = {}


def demodulate(symbols, filters, freqs, sampler):
    streams = []
    symbol_list = []
    errors = {}

    def error_handler(received, decoded, freq):
        errors.setdefault(freq, []).append(received / decoded)

    generators = common.split(symbols, n=len(freqs))
    for freq, S in zip(freqs, generators):
        equalized = []
        S = filters[freq](S)
        S = common.icapture(S, result=equalized)
        symbol_list.append(equalized)

        freq_handler = functools.partial(error_handler, freq=freq)
        bits = modem.qam.decode(S, freq_handler)  # list of bit tuples
        streams.append(bits)  # stream per frequency

    stats['symbol_list'] = symbol_list
    stats['rx_bits'] = 0
    stats['rx_start'] = time.time()

    log.info('Demodulation started')
    for i, block in enumerate(common.izip(*streams)):  # block per frequency
        for bits in block:
            stats['rx_bits'] = stats['rx_bits'] + len(bits)
            yield bits

        if i and i % config.baud == 0:
            err = np.array([e for v in errors.values() for e in v])
            correction = np.mean(np.angle(err)) / (2*np.pi) if len(err) else 0.0
            duration = time.time() - stats['rx_start']
            log.debug('%10.1f kB, realtime: %6.2f%%, sampling error: %+.3f%%',
                      stats['rx_bits'] / 8e3,
                      duration * 100.0 / (i*config.Tsym),
                      correction * 1e2)
            errors.clear()
            sampler.freq -= 0.01 * correction / config.Fc
            sampler.offset -= correction


def receive(signal, freqs, gain=1.0):
    symbols = sigproc.Demux(signal, freqs)
    symbols.sampler.gain = gain

    freq_err, offset_err = receive_prefix(symbols)
    symbols.sampler.offset -= offset_err
    symbols.sampler.freq -= freq_err

    filters = train_receiver(symbols, freqs)
    data_bits = demodulate(symbols, filters, freqs, symbols.sampler)
    return itertools.chain.from_iterable(data_bits)


def decode(bits_iterator):
    def blocks():
        while True:
            bits = itertools.islice(bits_iterator, 8 * ecc.BLOCK_SIZE)
            block = bitarray.bitarray(endian='little')
            block.extend(bits)
            if not block:
                break
            yield bytearray(block.tobytes())

    return ecc.decode(blocks())


def iread(fd):
    reader = stream.Reader(fd, data_type=common.loads)
    return itertools.chain.from_iterable(reader)


def main(args):
    try:
        log.info('Running MODEM @ {:.1f} kbps'.format(modem.modem_bps / 1e3))

        signal = iread(args.input)
        skipped = common.take(signal, args.skip)
        log.debug('Skipping %.3f seconds', len(skipped) / float(modem.baud))

        stream.check = common.check_saturation

        size = 0
        signal, amplitude = detect(signal, config.Fc)
        bits = receive(signal, modem.freqs, gain=1.0/amplitude)
        try:
            for chunk in decode(bits):
                args.output.write(chunk)
                size = size + len(chunk)
        except Exception:
            log.exception('Decoding failed')

        duration = time.time() - stats['rx_start']
        audio_time = stats['rx_bits'] / float(modem.modem_bps)
        log.debug('Demodulated %.3f kB @ %.3f seconds (%.1f%% realtime)',
                  stats['rx_bits'] / 8e3, duration, 100 * duration / audio_time)

        log.info('Received %.3f kB @ %.3f seconds = %.3f kB/s',
                 size * 1e-3, duration, size * 1e-3 / duration)

        pylab.figure()
        symbol_list = np.array(stats['symbol_list'])
        for i, freq in enumerate(modem.freqs):
            pylab.subplot(HEIGHT, WIDTH, i+1)
            constellation(symbol_list[i], modem.qam.symbols,
                          '$F_c = {} Hz$'.format(freq))
    except Exception as e:
        log.exception(e)
    finally:
        pylab.show()


def constellation(y, symbols, title):
    theta = np.linspace(0, 2*np.pi, 1000)
    pylab.plot(y.real, y.imag, '.:')
    pylab.plot(np.cos(theta), np.sin(theta), ':')
    points = np.array(symbols)
    pylab.plot(points.real, points.imag, '+')
    pylab.grid('on')
    pylab.axis('equal')
    pylab.title(title)
