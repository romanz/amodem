"""Asynchronous Reading capabilities for amodem."""

import logging
import threading

from queue import Queue

log = logging.getLogger()


class AsyncReader:
    def __init__(self, stream, bufsize):
        self.stream = stream
        self.queue = Queue()
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
        except BaseException:  # pylint: disable=broad-except
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
