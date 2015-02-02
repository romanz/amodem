import threading
import six  # since `Queue` module was renamed to `queue` (in Python 3)
import logging

log = logging.getLogger()


class AsyncReader(object):
    def __init__(self, stream, bufsize):
        self.stream = stream
        self.queue = six.moves.queue.Queue()
        self.stop = threading.Event()
        args = (stream, bufsize, self.queue, self.stop)
        self.thread = threading.Thread(target=AsyncReader._thread,
                                       args=args, name='AsyncReader')
        self.thread.start()
        self.buf = b''

    @staticmethod
    def _thread(src, bufsize, queue, stop):
        total = 0
        try:
            log.debug('AsyncReader thread started')
            while not stop.isSet():
                buf = src.read(bufsize)
                queue.put(buf)
                total += len(buf)
            log.debug('AsyncReader thread stopped (read %d bytes)', total)
        except:
            log.exception('AsyncReader thread failed')
            queue.put(None)

    def read(self, size):
        while len(self.buf) < size:
            buf = self.queue.get()
            if buf is None:
                raise IOError('cannot read from stream')
            self.buf += buf

        result = self.buf[:size]
        self.buf = self.buf[size:]
        return result

    def close(self):
        if self.stream is not None:
            self.stop.set()
            self.thread.join()
            self.stream.close()
            self.stream = None


class AsyncWriter(object):
    def __init__(self, stream):
        self.stream = stream
        self.queue = six.moves.queue.Queue()
        self.error = threading.Event()
        self.stop = threading.Event()
        self.args = (stream, self.queue, self.error)
        self.thread = None

    @staticmethod
    def _thread(dst, queue, error):
        total = 0
        try:
            log.debug('AsyncWriter thread started')
            while True:
                buf = queue.get(block=False)
                if buf is None:
                    break
                dst.write(buf)
                total += len(buf)
            log.debug('AsyncWriter thread stopped (written %d bytes)', total)
        except:
            log.exception('AsyncWriter thread failed')
            error.set()

    def write(self, buf):
        if self.error.isSet():
            raise IOError('cannot write to stream')

        self.queue.put(buf)
        if self.thread is None:
            self.thread = threading.Thread(target=AsyncWriter._thread,
                                           args=self.args, name='AsyncWriter')
            self.thread.start()  # start only after there is data to write

    def close(self):
        if self.stream is not None:
            self.queue.put(None)
            self.thread.join()
            self.stream.close()
            self.stream = None
