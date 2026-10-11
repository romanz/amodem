import subprocess as sp
import sys
from io import BytesIO

import numpy as np
import pytest

from .. import common, stream


@pytest.mark.parametrize('converter', [bytes, len])
def test_eof_reader_applies_data_type_to_every_block(converter):
    reader = stream.Reader(BytesIO(b'abcdef'), data_type=converter, eof=True)
    reader.bufsize = 4

    blocks = list(reader)
    expected = [converter(b'abcd'), converter(b'ef')]

    assert blocks == expected
    assert all(type(block) is type(value)
               for block, value in zip(blocks, expected))
    assert reader.total == 6


def test_eof_reader_converts_pcm_samples():
    expected = np.array([0.25, -0.5, 0.75])
    reader = stream.Reader(BytesIO(common.dumps(expected)),
                           data_type=common.loads, eof=True)
    reader.bufsize = 4

    blocks = list(reader)

    np.testing.assert_array_equal(np.concatenate(blocks), expected)
    assert reader.total == 6


def test_eof_reader_without_data_type_preserves_bytes():
    reader = stream.Reader(BytesIO(b'abcdef'), eof=True)
    reader.bufsize = 4

    assert list(reader) == [bytearray(b'abcd'), bytearray(b'ef')]


def test_empty_eof_reader_does_not_convert():
    calls = []
    reader = stream.Reader(BytesIO(), data_type=calls.append, eof=True)

    assert not list(reader)
    assert not calls
    assert reader.total == 0


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
