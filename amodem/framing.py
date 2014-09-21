''' Reed-Solomon CODEC. '''
from . import common
import bitarray

import functools
import itertools
import binascii
import struct
import logging
log = logging.getLogger(__name__)

_crc32 = lambda x, mask: binascii.crc32(x) & mask
# (so the result will be unsigned on Python 2/3)


class Checksum(object):
    fmt = '>L'  # unsigned longs (32-bit)
    size = struct.calcsize(fmt)
    func = functools.partial(_crc32, mask=0xFFFFFFFF)

    def encode(self, payload):
        checksum = self.func(payload)
        return struct.pack(self.fmt, checksum) + payload

    def decode(self, data):
        received, = struct.unpack(self.fmt, data[:self.size])
        payload = data[self.size:]
        expected = self.func(payload)
        if received != expected:
            log.warning('Invalid checksum: %04x != %04x', received, expected)
            raise ValueError('Invalid checksum')
        return payload


class Framer(object):
    block_size = 1024
    prefix_fmt = '>L'
    prefix_len = struct.calcsize(prefix_fmt)
    checksum = Checksum()

    EOF = b''

    def _pack(self, block):
        frame = self.checksum.encode(block)
        return struct.pack(self.prefix_fmt, len(frame)) + frame

    def encode(self, data):
        for _, block in common.iterate(data=data, size=self.block_size,
                                       func=bytearray, truncate=False):
            yield self._pack(block=block)
        yield self._pack(block=self.EOF)

    def decode(self, data):
        data = iter(data)
        while True:
            length, = self._take_fmt(data, self.prefix_fmt)
            frame = self._take_len(data, length)
            block = self.checksum.decode(frame)
            if block == self.EOF:
                log.debug('EOF frame detected')
                return

            yield block

    def _take_fmt(self, data, fmt):
        length = struct.calcsize(fmt)
        chunk = bytearray(itertools.islice(data, length))
        if len(chunk) < length:
            raise ValueError('missing prefix data')
        return struct.unpack(fmt, chunk)

    def _take_len(self, data, length):
        chunk = bytearray(itertools.islice(data, length))
        if len(chunk) < length:
            raise ValueError('missing payload data')
        return chunk


def chain_wrapper(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        result = func(*args, **kwargs)
        return itertools.chain.from_iterable(result)
    return wrapped


@chain_wrapper
def encode(data, framer=None):
    framer = framer or Framer()
    for frame in framer.encode(data):
        bits = bitarray.bitarray(endian='little')
        bits.frombytes(bytes(frame))
        yield bits


@chain_wrapper
def _to_bytes(bits, block_size=1):
    for _, chunk in common.iterate(data=bits, size=8*block_size,
                                   func=lambda x: x, truncate=True):
        yield bitarray.bitarray(chunk, endian='little').tobytes()


@chain_wrapper
def decode(bits, framer=None):
    framer = framer or Framer()
    for frame in framer.decode(_to_bytes(bits)):
        yield frame
