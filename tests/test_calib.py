from amodem import calib

from io import BytesIO


class ProcessMock(object):
    def __init__(self):
        self.buf = BytesIO()
        self.stdin = self
        self.stdout = self

    def __call__(self, *args, **kwargs):
        return self

    def kill(self):
        pass

    def write(self, data):
        self.buf.write(data)
        if self.buf.tell() > 1e6:
            raise KeyboardInterrupt

    def read(self, n):
        return self.buf.read(n)


def verify(msg):
    assert msg == calib.fmt.format(1, 1, 0, 1)


def test():
    p = ProcessMock()
    calib.send(p)
    p.buf.seek(0)
    calib.recv(p, reporter=verify)
