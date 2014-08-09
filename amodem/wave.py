import os
import signal
import subprocess as sp
import logging

log = logging.getLogger(__name__)

from . import config
Fs = int(config.Fs)  # sampling rate

bits_per_sample = 16
bytes_per_sample = bits_per_sample / 8.0
bytes_per_second = bytes_per_sample * Fs

audio_format = 'S{}_LE'.format(bits_per_sample)  # PCM signed little endian


def play(fname, **kwargs):
    args = ['aplay', fname, '-q', '-f', audio_format, '-c', '1', '-r', Fs]
    return launch(*args, **kwargs)


def record(fname, **kwargs):
    args = ['arecord', fname, '-q', '-f', audio_format, '-c', '1', '-r', Fs]
    return launch(*args, **kwargs)


def launch(*args, **kwargs):
    args = list(map(str, args))
    log.debug('$ %s', ' '.join(args))
    p = sp.Popen(args=args, **kwargs)
    p.stop = lambda: os.kill(p.pid, signal.SIGKILL)
    return p
