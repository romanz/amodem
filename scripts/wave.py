#!/usr/bin/env python
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

from amodem import wave

import argparse
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()
fmt = 'a raw audio file (16 bits at {:.1f} kHz)'.format(wave.Fs / 1e3)
recorder = subparsers.add_parser('record', help='record ' + fmt)
recorder.add_argument(
    'filename', default='-',
    help='path to the audio file to record (otherwise, use stdout)')
recorder.set_defaults(func=wave.record)

player = subparsers.add_parser('play', help='play ' + fmt)
player.add_argument(
    'filename', default='-',
    help='path to the audio file to play (otherwise, use stdin)')
player.set_defaults(func=wave.play)

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
