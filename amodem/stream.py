import time
import logging

log = logging.getLogger(__name__)


class Reader(object):

    def __init__(self, fd, data_type=None, bufsize=4096,
                 eof=False, timeout=2.0, wait=0.2):
        self.fd = fd
        self.data_type = data_type if (data_type is not None) else lambda x: x
        self.bufsize = bufsize
        self.eof = eof
        self.timeout = timeout
        self.wait = wait
        self.total = 0
        self.check = None

    def __iter__(self):
        return self

    def next(self):
        block = bytearray()
        if self.eof:
            data = self.fd.read(self.bufsize)
            if data:
                self.total += len(data)
                block.extend(data)
                return block
            else:
                raise StopIteration()

        finish_time = time.time() + self.timeout
        while time.time() <= finish_time:
            left = self.bufsize - len(block)
            data = self.fd.read(left)
            if data:
                self.total += len(data)
                block.extend(data)

            if len(block) == self.bufsize:
                values = self.data_type(block)
                if self.check:
                    self.check(values)
                return values

            time.sleep(self.wait)

        raise IOError('timeout')

    __next__ = next
