#!/usr/bin/env python
from amodem import calib

import argparse
p = argparse.ArgumentParser()
sub = p.add_subparsers()
sub.add_parser('send').set_defaults(func=calib.send)
sub.add_parser('recv').set_defaults(func=calib.recv)
args = p.parse_args()
args.func()
