import time



class Reader(object):

    SAMPLES = 4096
    BUFSIZE = int(SAMPLES * wave.bytes_per_sample)
    WAIT = 0.1
    TIMEOUT = 2.0

    def __init__(self, fd, data_type=None, bufsize=None, eof=False):
        self.fd = fd
        self.check = None
        self.total = 0
        self.bufsize = bufsize if (bufsize is not None) else self.BUFSIZE
        self.eof = eof
        self.data_type = data_type if (data_type is not None) else lambda x: x

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        block = bytearray()
        if self.eof:
            data = self.fd.read(self.BUFSIZE)
            if data:
                self.total += len(data)
                block.extend(data)
                return block
            else:
                raise StopIteration()

        finish_time = time.time() + self.TIMEOUT
        while time.time() <= finish_time:
            left = self.BUFSIZE - len(block)
            data = self.fd.read(left)
            if data:
                self.total += len(data)
                block.extend(data)

            if len(block) == self.BUFSIZE:
                values = self.data_type(block)
                if self.check:
                    self.check(values)
                return values

            time.sleep(self.WAIT)

        raise IOError('timeout')
