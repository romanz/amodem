import time
import itertools

import common
import wave


class Reader(object):

    SAMPLES = 4096
    BUFSIZE = int(SAMPLES * wave.bytes_per_sample)
    WAIT = 0.1
    TIMEOUT = 2.0

    def __init__(self, fd, bufsize=None, eof=False):
        self.fd = fd
        self.check = None
        self.total = 0
        self.bufsize = bufsize if (bufsize is not None) else self.BUFSIZE
        self.eof = eof

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        block = bytearray()
        finish_time = time.time() + self.TIMEOUT
        while time.time() <= finish_time:
            left = self.BUFSIZE - len(block)
            data = self.fd.read(left)
            if data:
                self.total += len(data)
                block.extend(data)
            elif self.eof:  # handle EOF condition by stopping iteration
                raise StopIteration()

            if len(block) == self.BUFSIZE:
                values = common.loads(str(block))
                if self.check:
                    self.check(values)
                return values

            time.sleep(self.WAIT)

        raise IOError('timeout')


def iread(fd):
    return itertools.chain.from_iterable(Reader(fd))
