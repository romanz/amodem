#!/usr/bin/env python
from amodem.sampling import resample
import sys

resample(src=sys.stdin, dst=sys.stdout, df=float(sys.argv[1]))
