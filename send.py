#!/usr/bin/env python
import numpy as np

import time
import logging
import itertools

log = logging.getLogger(__name__)

import sigproc
import train
from common import *

class Symbol(object):
    t       = np.arange(0, Nsym) * Ts
    carrier = [ np.exp(2j * np.pi * F * t) for F in frequencies ]

sym = Symbol()

data = open('data.send', 'r').read()

def write(fd, sym, n=1):
    fd.write(dumps(sym, n))

def start(sig, c):
    write(sig, c*0, n=50)
    write(sig, c*1, n=400)
    write(sig, c*0, n=50)

def training(sig, c):
    for b in train.equalizer:
        write(sig, c * b)

def modulate(sig, bits):
    symbols_iter = sigproc.modulator.encode(list(bits))
    symbols_iter = itertools.chain(symbols_iter, itertools.repeat(0))
    carriers = np.array(sym.carrier) / len(sym.carrier)
    while True:
        symbols = itertools.islice(symbols_iter, len(sym.carrier))
        symbols = np.array(list(symbols))
        write(sig, np.dot(symbols, carriers))
        if all(symbols == 0):
            break

def main():
    import ecc
    log.info('Running MODEM @ {:.1f} kbps'.format(sigproc.modem_bps / 1e3))

    with open('tx.int16', 'wb') as fd:
        start(fd, sym.carrier[carrier_index])
        for c in sym.carrier:
            training(fd, c)

        bits = to_bits(ecc.encode(data))
        modulate(fd, bits)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    main()
