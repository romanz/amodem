from amodem import calib
from amodem import config

from io import BytesIO


class ProcessMock(object):
    def __init__(self):
        self.buf = BytesIO()
        self.stdin = self
        self.stdout = self
        self.bytes_per_sample = 2

    def launch(self, *args, **kwargs):
        return self

    __call__ = launch

    def kill(self):
        pass

    def write(self, data):
        self.buf.write(data)
        if self.buf.tell() > 1e6:
            raise KeyboardInterrupt

    def read(self, n):
        return self.buf.read(n)


def test_success():
    p = ProcessMock()
    calib.send(config, p)
    p.buf.seek(0)
    calib.recv(config, p)


def test_errors():
    p = ProcessMock()

    def _write(data):
        raise IOError()
    p.write = _write
    calib.send(config, p)
    assert p.buf.tell() == 0

    def _read(data):
        raise KeyboardInterrupt()
    p.read = _read
    calib.recv(config, p, verbose=True)
    assert p.buf.tell() == 0
