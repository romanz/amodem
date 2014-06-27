import os
import signal
import subprocess as sp

from common import Fs

def play(fname, **kwargs):
    return launch('aplay', fname, '-q', '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs)), **kwargs)

def record(fname, **kwargs):
    return launch('arecord', fname, '-q', '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs)), **kwargs)

def launch(*args, **kwargs):
    print args
    p = sp.Popen(args=args, **kwargs)
    p.stop = lambda: os.kill(p.pid, signal.SIGINT)
    return p
