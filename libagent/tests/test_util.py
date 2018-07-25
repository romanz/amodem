import io

import mock
import pytest

from .. import util


def test_bytes2num():
    assert util.bytes2num(b'\x12\x34') == 0x1234


def test_num2bytes():
    assert util.num2bytes(0x1234, size=2) == b'\x12\x34'


def test_pack():
    assert util.pack('BHL', 1, 2, 3) == b'\x01\x00\x02\x00\x00\x00\x03'


def test_frames():
    msgs = [b'aaa', b'bb', b'c' * 0x12340]
    f = util.frame(*msgs)
    assert f == b'\x00\x01\x23\x45' + b''.join(msgs)
    assert util.read_frame(io.BytesIO(f)) == b''.join(msgs)


class FakeSocket:
    def __init__(self):
        self.buf = io.BytesIO()

    def sendall(self, data):
        self.buf.write(data)

    def recv(self, size):
        return self.buf.read(size)


def test_send_recv():
    s = FakeSocket()
    util.send(s, b'123')
    util.send(s, b'*')
    assert s.buf.getvalue() == b'123*'

    s.buf.seek(0)
    assert util.recv(s, 2) == b'12'
    assert util.recv(s, 2) == b'3*'

    pytest.raises(EOFError, util.recv, s, 1)


def test_crc24():
    assert util.crc24(b'') == b'\xb7\x04\xce'
    assert util.crc24(b'1234567890') == b'\x8c\x00\x72'


def test_bit():
    assert util.bit(6, 3) == 0
    assert util.bit(6, 2) == 1
    assert util.bit(6, 1) == 1
    assert util.bit(6, 0) == 0


def test_split_bits():
    assert util.split_bits(0x1234, 4, 8, 4) == [0x1, 0x23, 0x4]


def test_hexlify():
    assert util.hexlify(b'\x12\x34\xab\xcd') == '1234ABCD'


def test_low_bits():
    assert util.low_bits(0x1234, 12) == 0x234
    assert util.low_bits(0x1234, 32) == 0x1234
    assert util.low_bits(0x1234, 0) == 0


def test_readfmt():
    stream = io.BytesIO(b'ABC\x12\x34')
    assert util.readfmt(stream, 'B') == (65,)
    assert util.readfmt(stream, '>2sH') == (b'BC', 0x1234)


def test_prefix_len():
    assert util.prefix_len('>H', b'ABCD') == b'\x00\x04ABCD'


def test_reader():
    stream = io.BytesIO(b'ABC\x12\x34')
    r = util.Reader(stream)
    assert r.read(1) == b'A'
    assert r.readfmt('2s') == b'BC'

    dst = io.BytesIO()
    with r.capture(dst):
        assert r.readfmt('>H') == 0x1234
    assert dst.getvalue() == b'\x12\x34'

    with pytest.raises(EOFError):
        r.read(1)


def test_setup_logging():
    util.setup_logging(verbosity=10, filename='/dev/null')


def test_memoize():
    f = mock.Mock(side_effect=lambda x: x)

    def func(x):
        # mock.Mock doesn't work with functools.wraps()
        return f(x)

    g = util.memoize(func)
    assert g(1) == g(1)
    assert g(1) != g(2)
    assert f.mock_calls == [mock.call(1), mock.call(2)]


def test_assuan_serialize():
    assert util.assuan_serialize(b'') == b''
    assert util.assuan_serialize(b'123\n456') == b'123%0A456'
    assert util.assuan_serialize(b'\r\n') == b'%0D%0A'


def test_cache():
    timer = mock.Mock(side_effect=range(7))
    c = util.ExpiringCache(seconds=2, timer=timer)  # t=0
    assert c.get() is None                          # t=1
    obj = 'foo'
    c.set(obj)                                      # t=2
    assert c.get() is obj                           # t=3
    assert c.get() is obj                           # t=4
    assert c.get() is None                          # t=5
    assert c.get() is None                          # t=6


def test_cache_inf():
    timer = mock.Mock(side_effect=range(6))
    c = util.ExpiringCache(seconds=float('inf'), timer=timer)
    obj = 'foo'
    c.set(obj)
    assert c.get() is obj
    assert c.get() is obj
    assert c.get() is obj
    assert c.get() is obj
