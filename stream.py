import time
import common
import wave


class FileBuffer(object):

    SAMPLES = 4096
    BUFSIZE = int(SAMPLES * wave.bytes_per_sample)
    WAIT = 0.1
    TIMEOUT = 2.0

    def __init__(self, fd):
        self.fd = fd

    def __iter__(self):
        return self

    def next(self):
        block = bytearray()
        finish_time = time.time() + self.TIMEOUT
        while time.time() <= finish_time:
            left = self.BUFSIZE - len(block)
            data = self.fd.read(left)
            if data:
                block.extend(data)
            if len(block) == self.BUFSIZE:
                _, values = common.loads(str(block))
                return values

            time.sleep(self.WAIT)

        raise IOError('timeout')
