import mock
import time
import pytest
from amodem import async
import logging

logging.basicConfig(format='%(message)s')


def test_async_reader():
    def _read(n):
        time.sleep(n * 0.1)
        return b'\x00' * n
    s = mock.Mock()
    s.read = _read
    r = async.AsyncReader(s, 1)

    n = 5
    assert r.read(n) == b'\x00' * n
    r.close()
    assert r.stream is None
    r.close()


def test_async_write():
    result = []

    def _write(buf):
        time.sleep(len(buf) * 0.1)
        result.append(buf)
    s = mock.Mock()
    s.write = _write
    w = async.AsyncWriter(s)

    w.write('foo')
    w.write(' ')
    w.write('bar')
    w.close()
    assert w.stream is None
    w.close()
    assert result == ['foo', ' ', 'bar']


def test_async_reader_error():
    s = mock.Mock()
    s.read.side_effect = IOError()
    r = async.AsyncReader(s, 1)
    with pytest.raises(IOError):
        r.read(3)


def test_async_writer_error():
    s = mock.Mock()
    s.write.side_effect = IOError()
    w = async.AsyncWriter(s)
    w.write('123')
    w.thread.join()
    with pytest.raises(IOError):
        w.write('456')
    assert s.write.mock_calls == [mock.call('123')]


def test_underflow():
    s = mock.Mock()
    w = async.AsyncWriter(s)
    w.write('blah')
    w.thread.join()
    assert s.write.mock_calls == [mock.call('blah')]
    with pytest.raises(IOError):
        w.write('xyzw')
