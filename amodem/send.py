#!/usr/bin/env python
import numpy as np
import sys
import logging
import itertools
import time

log = logging.getLogger(__name__)

from . import train
from . import wave

from . import common
from . import config
from . import sigproc
from . import stream
from . import ecc

modem = sigproc.MODEM(config)


class Symbol(object):
    def __init__(self):
        t = np.arange(0, config.Nsym) * config.Ts
        self.carrier = [np.exp(2j * np.pi * F * t) for F in modem.freqs]

sym = Symbol()


class Writer(object):
    def __init__(self):
        self.last = time.time()
        self.offset = 0

    def write(self, fd, sym, n=1):
        data = common.dumps(sym, n)
        fd.write(data)
        self.offset += len(data)
        if time.time() > self.last + 1:
            log.debug('%10.3f seconds of data audio',
                      self.offset / wave.bytes_per_second)
            self.last += 1

writer = Writer()


def start(fd, c):
    for value in train.prefix:
        writer.write(fd, c * value)


def training(fd, c):
    for b in train.equalizer:
        writer.write(fd, c * b)


def modulate(fd, bits):
    symbols_iter = modem.qam.encode(bits)
    symbols_iter = itertools.chain(symbols_iter, itertools.repeat(0))
    carriers = np.array(sym.carrier) / len(sym.carrier)
    while True:
        symbols = itertools.islice(symbols_iter, len(sym.carrier))
        symbols = np.array(list(symbols))
        writer.write(fd, np.dot(symbols, carriers))
        if all(symbols == 0):  # EOF marker
            break


def main(args):
    log.info('Running MODEM @ {:.1f} kbps'.format(modem.modem_bps / 1e3))

    # padding audio with silence
    writer.write(args.output, np.zeros(int(config.Fs * args.silence_start)))

    start(args.output, sym.carrier[config.carrier_index])
    for c in sym.carrier:
        training(args.output, c)
    training_size = writer.offset
    log.info('%.3f seconds of training audio',
             training_size / wave.bytes_per_second)

    reader = stream.Reader(args.input, bufsize=(64 << 10), eof=True)
    data = itertools.chain.from_iterable(reader)
    encoded = itertools.chain.from_iterable(ecc.encode(data))
    modulate(args.output, bits=common.to_bits(encoded))

    data_size = writer.offset - training_size
    log.info('%.3f seconds of data audio, for %.3f kB of data',
             data_size / wave.bytes_per_second, reader.total / 1e3)

    # padding audio with silence
    writer.write(args.output, np.zeros(int(config.Fs * args.silence_stop)))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-12s %(message)s')

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--silence-start', type=float, default=1.0)
    p.add_argument('--silence-stop', type=float, default=1.0)
    p.add_argument('-i', '--input', type=argparse.FileType('rb'),
                   default=sys.stdin)
    p.add_argument('-o', '--output', type=argparse.FileType('wb'),
                   default=sys.stdout)
    args = p.parse_args()
    main(args)
