import time


class Reader:

    wait = 0.2
    timeout = 2.0
    bufsize = (8 << 10)

    def __init__(self, fd, data_type=None, eof=False):
        self.fd = fd
        self.data_type = data_type if (data_type is not None) else lambda x: x
        self.eof = eof
        self.total = 0

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
            raise StopIteration()

        finish_time = time.time() + self.timeout
        while time.time() <= finish_time:
            left = self.bufsize - len(block)
            data = self.fd.read(left)
            if data:
                self.total += len(data)
                block.extend(data)

            if len(block) == self.bufsize:
                return self.data_type(block)

            time.sleep(self.wait)

        raise IOError('timeout')

    __next__ = next


class Dumper:
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst

    def read(self, size):
        data = self.src.read(size)
        self.dst.write(data)
        return data
