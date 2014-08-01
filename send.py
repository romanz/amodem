#!/usr/bin/env python
import numpy as np
import sys
import logging
import itertools
import time

log = logging.getLogger(__name__)

import train
import wave

import common
import config
import sigproc

modem = sigproc.MODEM(config)


class Symbol(object):
    t = np.arange(0, config.Nsym) * config.Ts
    carrier = [np.exp(2j * np.pi * F * t) for F in modem.freqs]

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
    writer.write(fd, c*1, n=400)
    writer.write(fd, c*0, n=50)


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


class Reader(object):
    def __init__(self, fd, size):
        self.fd = fd
        self.size = size
        self.total = 0

    def next(self):
        block = self.fd.read(self.size)
        if block:
            self.total += len(block)
            return block
        else:
            raise StopIteration()

    def __iter__(self):
        return self


def main(args):
    import ecc
    log.info('Running MODEM @ {:.1f} kbps'.format(modem.modem_bps / 1e3))

    fd = sys.stdout

    # padding audio with silence
    writer.write(fd, np.zeros(int(config.Fs * args.silence_start)))

    start(fd, sym.carrier[config.carrier_index])
    for c in sym.carrier:
        training(fd, c)
    training_size = writer.offset
    log.info('%.3f seconds of training audio',
             training_size / wave.bytes_per_second)

    reader = Reader(sys.stdin, 64 << 10)
    data = itertools.chain.from_iterable(reader)
    encoded = itertools.chain.from_iterable(ecc.encode(data))
    modulate(fd, bits=common.to_bits(encoded))

    data_size = writer.offset - training_size
    log.info('%.3f seconds of data audio, for %.3f kB of data',
             data_size / wave.bytes_per_second, reader.total / 1e3)

    # padding audio with silence
    writer.write(fd, np.zeros(int(config.Fs * args.silence_stop)))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-12s %(message)s')

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--silence-start', type=float, default=1.0)
    p.add_argument('--silence-stop', type=float, default=1.0)
    args = p.parse_args()
    main(args)
