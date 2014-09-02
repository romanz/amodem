#!/usr/bin/env python
import sys
if sys.version_info.major == 2:
    _stdin = sys.stdin
    _stdout = sys.stdout
else:
    _stdin = sys.stdin.buffer
    _stdout = sys.stdout.buffer

import logging
format = '%(asctime)s %(levelname)-10s %(message)-100s %(filename)s:%(lineno)d'
logging.basicConfig(level=logging.DEBUG, format=format)

import amodem.recv
import amodem.send
import amodem.wave

import argparse

def FileType(mode, process=None):
    def opener(fname):
        assert 'r' in mode or 'w' in mode
        if process is None and fname is None:
            fname = '-'

        if fname is None:
            if 'r' in mode: return process(stdout=amodem.wave.sp.PIPE).stdout
            if 'w' in mode: return process(stdin=amodem.wave.sp.PIPE).stdin

        if fname == '-':
            if 'r' in mode: return _stdin
            if 'w' in mode: return _stdout

        return open(fname, mode)

    return opener


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-i', '--input')
    p.add_argument('-o', '--output')

    sub = p.add_subparsers()

    send = sub.add_parser('send')
    send.add_argument('--silence-start', type=float, default=1.0,
                      help='seconds of silence before transmission starts')
    send.add_argument('--silence-stop', type=float, default=1.0,
                      help='seconds of silence after transmission stops')

    send.set_defaults(main=amodem.send.main,
        input_type=FileType('rb'),
        output_type=FileType('wb', amodem.wave.play)
    )

    recv = sub.add_parser('recv')
    recv.add_argument('--skip', type=int, default=128,
                      help='skip initial N samples, due to spurious spikes')
    recv.add_argument('--plot', dest='plt', action='store_true', default=False,
                      help='plot results using pylab module')
    recv.set_defaults(main=amodem.recv.main,
        input_type=FileType('rb', amodem.wave.record),
        output_type=FileType('wb')
    )

    args = p.parse_args()
    args.input = args.input_type(args.input)
    args.output = args.output_type(args.output)
    args.main(args)


if __name__ == '__main__':
    main()
