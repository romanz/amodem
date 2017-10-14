#!/usr/bin/env python
from amodem.sampling import resample
import argparse
import sys

"""Script that exposes the amodem.resample() function 
to the command line, taking parameters via standard 
inputs and returning results via standard outputs.
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument('df', type=float)
    args = p.parse_args()

    resample(src=sys.stdin, dst=sys.stdout, df=args.df)

if __name__ == '__main__':
    main()
