#!/usr/bin/env python
import sys
import binascii

lines = sys.stdin.read().strip().split('\n')
for line in lines:
    try:
        head, tail = line.split(' ', 1)
    except ValueError:
        print line
        continue

    bars = ''
    try:
        data = binascii.unhexlify(head)
        data = map(ord, data)
        bars = ['\033[48;5;%dm%02x\033[m' % (x, x) for x in data]
        head = ''.join(bars)
    except TypeError:
        pass

    print('%s %s' % (head, tail))
