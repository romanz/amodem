from matplotlib import pyplot as plt
import subprocess as sp
import numpy as np

import os
import sys
import time
import signal
import logging
import itertools

logging.basicConfig(level=0, format='%(message)s')
log = logging.getLogger(__name__)

import sigproc
from common import *

dev_null = open('/dev/null')

def play(fd):
    args = ['aplay', fd.name, '-q', '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs))]
    ret = sp.call(args=args)
    assert ret == 0

def record(fname):
    args = ['arecord', fname, '-q', '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs))]
    p = sp.Popen(args=args)
    p.stop = lambda: os.kill(r.pid, signal.SIGINT)
    return p


log.info('MODEM Fc={}KHz, {} BAUD'.format(Fc/1e3, baud))


class Symbol(object):
    t       = np.arange(0, Nsym) * Ts
    c0      = np.exp(2j * np.pi * F0 * t)
    c1      = np.exp(2j * np.pi * F1 * t)

sym = Symbol()

data = open('data.send', 'r').read()

def start(sig, c):
    sig.send(c*0, n=100)
    sig.send(c*1, n=300)
    sig.send(c*0, n=100)

def train(sig, c):
    for i in range(20):
        sig.send(c*1, n=10)
        sig.send(c*0, n=10)
    sig.send(c*0, n=100)

if __name__ == '__main__':

    with open('tx.int16', 'wb') as fd:
        sig = Signal(fd)
        start(sig, sym.c0)
        train(sig, sym.c0)
        train(sig, sym.c1)
        carriers = [sym.c0, sym.c1]

        bits = to_bits(pack(data))
        symbols_iter = sigproc.modulator.encode(list(bits))
        symbols_iter = itertools.chain(symbols_iter, itertools.repeat(0))
        while True:
            symbols = itertools.islice(symbols_iter, len(carriers))
            symbols = np.array(list(symbols))
            sig.send(np.dot(symbols, carriers))
            if all(symbols == 0):
                break


    r = record('rx.int16')
    start = time.time()
    p = play(fd)
    log.debug('Took %.2f seconds', time.time() - start)
    time.sleep(0.1)
    r.stop()
