#!/usr/bin/env python
import sys
import binascii

lines = sys.stdin.read().strip().split('\n')
for line in lines:
    head, tail = line.split(' ', 1)
    bars = ''
    try:
        data = binascii.unhexlify(head)
        data = map(ord, data)
        bars = ['\033[48;5;%dm \033[m' % (x,) for x in data]
        bars = ''.join(bars)
    except TypeError:
        pass

    print('%s: %s %s' % (bars, head, tail))
