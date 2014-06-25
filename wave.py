import os
import signal
import subprocess as sp

from common import Fs

def play(fd):
    args = ['aplay', fd.name, '-q', '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs))]
    ret = sp.call(args=args)
    assert ret == 0

def record(fname):
    args = ['arecord', fname, '-q', '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs))]
    p = sp.Popen(args=args)
    p.stop = lambda: os.kill(p.pid, signal.SIGINT)
    return p


