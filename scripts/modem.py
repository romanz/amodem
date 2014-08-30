#!/usr/bin/env python
import sys
if sys.version_info.major == 2:
    _stdin = sys.stdin
    _stdout = sys.stdout
else:
    _stdin = sys.stdin.buffer
    _stdout = sys.stdout.buffer
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-12s %(message)s')

import amodem.recv
import amodem.send

import argparse
p = argparse.ArgumentParser()
p.add_argument('-i', '--input',
               type=argparse.FileType('rb'),
               default=_stdin)
p.add_argument('-o', '--output',
               type=argparse.FileType('wb'),
               default=_stdout)

sub = p.add_subparsers()

send = sub.add_parser('send')
send.add_argument('--silence-start', type=float, default=1.0)
send.add_argument('--silence-stop', type=float, default=1.0)
send.set_defaults(func=amodem.send.main)

recv = sub.add_parser('recv')
recv.add_argument('--skip', type=int, default=128,
                  help='skip initial N samples, due to spurious spikes')
recv.add_argument('--plot', dest='plt', action='store_true', default=False,
                  help='plot results using pylab module')
recv.set_defaults(func=amodem.recv.main)

args = p.parse_args()
args.func(args)
