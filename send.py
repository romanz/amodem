#!/usr/bin/env python
import numpy as np
import sys
import logging
import itertools
import time

log = logging.getLogger(__name__)

import sigproc
import train
import wave

from common import *


class Symbol(object):
    t = np.arange(0, Nsym) * Ts
    carrier = [np.exp(2j * np.pi * F * t) for F in frequencies]

sym = Symbol()


class Writer(object):
    def __init__(self):
        self.last = time.time()

    def write(self, fd, sym, n=1):
        fd.write(dumps(sym, n))
        if time.time() > self.last + 1:
            log.debug('%10.3f seconds of data audio',
                      fd.tell() / wave.bytes_per_second)
            self.last += 1

write = Writer().write


def start(fd, c):
    write(fd, c*1, n=400)
    write(fd, c*0, n=50)


def training(fd, c):
    for b in train.equalizer:
        write(fd, c * b)


def modulate(fd, bits):
    symbols_iter = sigproc.modulator.encode(bits)
    symbols_iter = itertools.chain(symbols_iter, itertools.repeat(0))
    carriers = np.array(sym.carrier) / len(sym.carrier)
    while True:
        symbols = itertools.islice(symbols_iter, len(sym.carrier))
        symbols = np.array(list(symbols))
        write(fd, np.dot(symbols, carriers))
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
    log.info('Running MODEM @ {:.1f} kbps'.format(sigproc.modem_bps / 1e3))

    fd = sys.stdout

    # padding audio with silence
    write(fd, np.zeros(int(Fs * args.silence_start)))

    start(fd, sym.carrier[carrier_index])
    for c in sym.carrier:
        training(fd, c)
    training_size = fd.tell()
    log.info('%.3f seconds of training audio',
             training_size / wave.bytes_per_second)

    reader = Reader(sys.stdin, 64 << 10)
    data = itertools.chain.from_iterable(reader)
    encoded = itertools.chain.from_iterable(ecc.encode(data))
    modulate(fd, bits=to_bits(encoded))

    data_size = fd.tell() - training_size
    log.info('%.3f seconds of data audio, for %.3f kB of data',
             data_size / wave.bytes_per_second, reader.total / 1e3)

    # padding audio with silence
    write(fd, np.zeros(int(Fs * args.silence_stop)))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-12s %(message)s')

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--silence-start', type=float, default=1.0)
    p.add_argument('--silence-stop', type=float, default=1.0)
    args = p.parse_args()
    main(args)
