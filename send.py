#!/usr/bin/env python
import numpy as np
import sys
import logging
import itertools

log = logging.getLogger(__name__)

import sigproc
import train
import wave
import stream

from common import *


class Symbol(object):
    t = np.arange(0, Nsym) * Ts
    carrier = [np.exp(2j * np.pi * F * t) for F in frequencies]

sym = Symbol()


def write(fd, sym, n=1):
    fd.write(dumps(sym, n))


def start(fd, c):
    write(fd, c*0, n=50)
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
        if all(symbols == 0):
            break


def iread(fd, size):
    while True:
        block = fd.read(size)
        if block:
            yield block
        else:
            return


def main(fname):
    import ecc
    log.info('Running MODEM @ {:.1f} kbps'.format(sigproc.modem_bps / 1e3))

    with open(fname, 'wb') as fd:
        start(fd, sym.carrier[carrier_index])
        for c in sym.carrier:
            training(fd, c)
        training_size = fd.tell()
        log.info('%.3f seconds of training audio',
                 training_size / wave.bytes_per_second)

        data = itertools.chain.from_iterable(iread(sys.stdin, 64 << 10))
        encoded = itertools.chain.from_iterable(ecc.encode(data))
        modulate(fd, bits=to_bits(encoded))

        data_size = fd.tell() - training_size
        log.info('%.3f seconds of data audio',
                 data_size / wave.bytes_per_second)
        # padding audio with silence
        fd.write('\x00' * int(wave.bytes_per_second))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)-12s %(message)s')

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('fname')
    args = p.parse_args()
    main(fname=args.fname)
