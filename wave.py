#!/usr/bin/env python
import os
import signal
import subprocess as sp
import logging

log = logging.getLogger(__name__)

from common import Fs
Fs = int(Fs) # sampling rate
bits_per_sample = 16
bytes_per_second = bits_per_sample * Fs / 8.0

audio_format = 'S{}_LE'.format(bits_per_sample) # PCM signed little endian

def play(fname, **kwargs):
    return launch('aplay', fname, '-q', '-f', audio_format, '-c', '1', '-r', Fs, **kwargs)

def record(fname, **kwargs):
    return launch('arecord', fname, '-q', '-f', audio_format, '-c', '1', '-r', Fs, **kwargs)

def launch(*args, **kwargs):
    args = map(str, args)
    log.debug('$ %s', ' '.join(args))
    p = sp.Popen(args=args, **kwargs)
    p.stop = lambda: os.kill(p.pid, signal.SIGINT)
    return p

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    fmt = 'a raw audio file (16 bits at {:.1f} kHz)'.format(Fs / 1e3)
    recorder = subparsers.add_parser('record', help='record ' + fmt)
    recorder.add_argument('filename', default='-', help='path to the audio file to record (otherwise, use stdout)')
    recorder.set_defaults(func=record)

    player = subparsers.add_parser('play', help='play ' + fmt)
    player.add_argument('filename', default='-', help='path to the audio file to play (otherwise, use stdin)')
    player.set_defaults(func=play)

    args = parser.parse_args()
    p = args.func(args.filename)

    import sys
    exitcode = 0
    try:
        exitcode = p.wait()
    except KeyboardInterrupt:
        p.kill()
        exitcode = p.wait()

    sys.exit(exitcode)
