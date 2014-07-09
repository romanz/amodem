import os
import signal
import subprocess as sp
import logging

log = logging.getLogger(__name__)

from common import Fs

def play(fname, **kwargs):
    return launch('aplay', fname, '-q', '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs)), **kwargs)

def record(fname, **kwargs):
    return launch('arecord', fname, '-q', '-f', 'S16_LE', '-c', '1', '-r', str(int(Fs)), **kwargs)

def launch(*args, **kwargs):
    log.debug('$ %s', ' '.join(args))
    p = sp.Popen(args=args, **kwargs)
    p.stop = lambda: os.kill(p.pid, signal.SIGINT)
    return p
