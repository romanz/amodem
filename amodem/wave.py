import os
import signal
import subprocess as sp
import logging
import functools

log = logging.getLogger(__name__)

from . import config
Fs = int(config.Fs)  # sampling rate

bits_per_sample = 16
bytes_per_sample = bits_per_sample / 8.0
bytes_per_second = bytes_per_sample * Fs

audio_format = 'S{}_LE'.format(bits_per_sample)  # PCM signed little endian


def launch(tool, fname='-', **kwargs):
    args = [tool, fname, '-q', '-f', audio_format, '-c', '1', '-r', str(Fs)]
    log.debug('running: %r', args)
    p = sp.Popen(args=args, **kwargs)
    p.stop = lambda: os.kill(p.pid, signal.SIGKILL)
    return p


# Use ALSA tools for audio playing/recording
play = functools.partial(launch, tool='aplay')
record = functools.partial(launch, tool='arecord')
