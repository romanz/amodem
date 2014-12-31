from amodem import calib
from amodem import config
config = config.fastest()

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
    class WriteError(ProcessMock):
        def write(self, data):
            raise IOError()
    p = WriteError()
    calib.send(config, p)
    assert p.buf.tell() == 0

    class ReadError(ProcessMock):
        def read(self, n):
            raise KeyboardInterrupt()
    p = ReadError()
    calib.recv(config, p, verbose=True)
    assert p.buf.tell() == 0
