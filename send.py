from matplotlib import pyplot as plt
import subprocess as sp
import numpy as np

import os
import sys
import time
import signal
import logging
logging.basicConfig(level=0, format='%(message)s')
log = logging.getLogger(__name__)

import sigproc
from common import *

def play(fd):
    args = ['aplay', fd.name, '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs))]
    ret = sp.call(args=args)
    assert ret == 0

def record(fname):
    args = ['arecord', fname, '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs))]
    p = sp.Popen(args=args)
    p.stop = lambda: os.kill(r.pid, signal.SIGINT)
    return p


log.info('MODEM Fc={}KHz, {} BAUD'.format(Fc/1e3, baud))


class Symbol(object):
    t       = np.arange(0, Nsym) * Ts
#    c0      = np.sin(2 * np.pi * F0 * t)
#    c1      = np.sin(2 * np.pi * F1 * t)
    carrier = np.exp(2j * np.pi * Fc * t)

class Signal(object):
    def __init__(self, fd):
        self.fd = fd
    def send(self, sym, n=1):
        sym = sym.imag * scaling
        sym = sym.astype('int16')
        for i in range(n):
            sym.tofile(fd)

sym = Symbol()

data = open('data.send', 'r').read()
data = pack(data)

bits = list(to_bits(data))

if __name__ == '__main__':

    with open('tx.int16', 'wb') as fd:
        sig = Signal(fd)
        sig.send(sym.carrier*0, n=100)
        sig.send(sym.carrier*1, n=300)
        sig.send(sym.carrier*0, n=100)
        for i in range(20):
            sig.send(sym.carrier*1, n=10)
            sig.send(sym.carrier*0, n=10)

        sig.send(sym.carrier*0, n=100)
        for s in sigproc.qpsk.encode(bits):
            sig.send(sym.carrier * s)


    r = record('rx.int16')
    p = play(fd)
    time.sleep(0.2)
    r.stop()
