import io

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


class SocketMock(object):
    def __init__(self):
        self.buf = io.BytesIO()

    def sendall(self, data):
        self.buf.write(data)

    def recv(self, size):
        return self.buf.read(size)


def test_send_recv():
    s = SocketMock()
    util.send(s, b'123')
    util.send(s, data=[42], fmt='B')
    assert s.buf.getvalue() == b'123*'

    s.buf.seek(0)
    assert util.recv(s, 2) == b'12'
    assert util.recv(s, 2) == b'3*'

    pytest.raises(EOFError, util.recv, s, 1)
