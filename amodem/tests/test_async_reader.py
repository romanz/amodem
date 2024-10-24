import logging
import time

import mock
import pytest

from .. import async_reader


logging.basicConfig(format='%(message)s')


def test_async_reader():
    def _read(n):
        time.sleep(n * 0.1)
        return b'\x00' * n
    s = mock.Mock()
    s.read = _read
    r = async_reader.AsyncReader(s, 1)

    n = 5
    assert r.read(n) == b'\x00' * n
    r.close()
    assert r.stream is None
    r.close()


def test_async_reader_error():
    s = mock.Mock()
    s.read.side_effect = IOError()
    r = async_reader.AsyncReader(s, 1)
    with pytest.raises(IOError):
        r.read(3)
