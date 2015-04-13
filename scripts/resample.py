#!/usr/bin/env python
from amodem.sampling import resample
import argparse
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument('df', type=float)
    args = p.parse_args()

    resample(src=sys.stdin, dst=sys.stdout, df=args.df)

if __name__ == '__main__':
    main()
