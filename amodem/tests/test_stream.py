from amodem import stream
import subprocess as sp
import sys

script = br"""
import sys
import time
import os

while True:
    time.sleep(0.1)
    sys.stdout.write('\x00' * 6400)
    sys.stderr.write('.')
"""


def test_read():
    p = sp.Popen(args=[sys.executable, '-'], stdin=sp.PIPE, stdout=sp.PIPE)
    p.stdin.write(script)
    p.stdin.close()
    f = stream.Reader(p.stdout)

    result = list(zip(range(10), f))
    p.kill()

    j = 0
    for i, buf in result:
        assert i == j
        assert len(buf) == f.bufsize
        j += 1

    try:
        next(f)
    except IOError as e:
        assert e.args == ('timeout',)
