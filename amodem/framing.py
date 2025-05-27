import binascii
import functools
import itertools
import logging
import struct

from . import common
from . import rs_codec

log = logging.getLogger(__name__)


def _checksum_func(x):
    return binascii.crc32(bytes(x))


class Checksum:
    fmt = '>L'  # crc32 unsigned longs (32-bit)
    size = struct.calcsize(fmt)

    def encode(self, payload, enable_correction=False, is_last_block=False):
        checksum = _checksum_func(payload)
        if enable_correction and is_last_block:
            checksum = _checksum_func(struct.pack(self.fmt, checksum))
        encoded = struct.pack(self.fmt, checksum) + payload
        return encoded

    def decode(self, data, enable_correction=False):
        received, = struct.unpack(self.fmt, bytes(data[:self.size]))
        payload = data[self.size:]
        expected = _checksum_func(payload)
        if not enable_correction:
            eof_detected = False
            valid_fail = received != expected
        else:
            eof_detected = received == _checksum_func(struct.pack(self.fmt, expected))
            valid_fail = received != expected and not eof_detected
        if valid_fail:
            log.warning('Invalid checksum: %08x != %08x', received, expected)
            raise ValueError('Invalid checksum')
        log.debug('Good checksum: %08x', received)
        return payload, eof_detected


class Framer:
    chunk_size = 255
    prefix_fmt = '>B'
    prefix_len = struct.calcsize(prefix_fmt)
    fid_fmt = '>H'
    fid_len = struct.calcsize(fid_fmt)
    crc32_len = 4  # 4 bytes crc

    enable_correction_chunk_size = chunk_size - rs_codec.RSCodecProvider.get_num_symbols()
    enable_correction_data_size = enable_correction_chunk_size - fid_len - prefix_len - crc32_len
    raw_data_size = chunk_size - prefix_len - crc32_len

    checksum = Checksum()

    EOF = b''
    NULL = b'\x00'

    def __init__(self):
        self.frame_id = 0

    def _pack(self, block, enable_correction=False, is_last_block=False):
        frame = self.checksum.encode(block, enable_correction=enable_correction, is_last_block=is_last_block)
        frame_id = self.frame_id
        self.frame_id += 1
        if not enable_correction:
            packed = bytearray(struct.pack(self.prefix_fmt, len(frame)) + frame)
            return packed
        else:
            # add frame_id at head
            packed = bytearray(
                struct.pack(self.fid_fmt, frame_id) + struct.pack(self.prefix_fmt, len(frame)) + frame)
            padded_size = self.enable_correction_chunk_size

            current_length = len(packed)
            if current_length > padded_size:
                raise ValueError(f"Packed data length ({current_length}) exceeds target length ({padded_size})")
            packed.extend(b'\x00' * (padded_size - current_length))
            return rs_codec.encrypt_pack(packed), frame_id

    def encode(self, data, enable_correction=False):
        if not enable_correction:
            iterator = common.iterate(data=data, size=self.raw_data_size, func=bytearray, truncate=False)
        else:
            iterator = common.iterate(data=data, size=self.enable_correction_data_size, func=bytearray, truncate=False)
        prev_block = next(iterator, None)
        for current_block in iterator:
            yield self._pack(block=prev_block, enable_correction=enable_correction)
            prev_block = current_block

        if prev_block is not None:
            yield self._pack(block=prev_block, enable_correction=enable_correction, is_last_block=enable_correction)

        if not enable_correction:
            # Add EOF block
            yield self._pack(block=self.EOF)

    def decode(self, data, enable_correction=False, raise_err=True):
        data = iter(data)
        while True:
            try:
                if not enable_correction:
                    pack = data
                else:
                    pack = rs_codec.decrypt_pack(data, self.chunk_size)
                    frame_id, = _take_fmt(pack, self.fid_fmt)

                length, = _take_fmt(pack, self.prefix_fmt)
                frame = _take_len(pack, length)
                block, eof_detected = self.checksum.decode(frame, enable_correction=enable_correction)

                if block == self.EOF:
                    log.debug('EOF frame detected')
                    return

                if not enable_correction:
                    yield block
                else:
                    yield block, frame_id
                    self.frame_id = frame_id

                if eof_detected:
                    log.debug('End frame detected')
                    return
            except Exception as e:
                if raise_err:
                    raise e
                else:
                    if not enable_correction:
                        yield self.NULL
                    else:
                        self.frame_id += 1
                        yield self.NULL, self.frame_id


def _take_fmt(data, fmt):
    length = struct.calcsize(fmt)
    chunk = bytearray(itertools.islice(data, length))
    if len(chunk) < length:
        raise ValueError('missing prefix data')
    return struct.unpack(fmt, bytes(chunk))


def _take_len(data, length):
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


class BitPacker:
    byte_size = 8

    def __init__(self):
        bits_list = []
        for index in range(2 ** self.byte_size):
            bits = [index & (2 ** k) for k in range(self.byte_size)]
            bits_list.append(tuple((1 if b else 0) for b in bits))

        self.to_bits = dict((i, bits) for i, bits in enumerate(bits_list))
        self.to_byte = dict((bits, i) for i, bits in enumerate(bits_list))


@chain_wrapper
def encode(data, framer=None, enable_correction=False):
    converter = BitPacker()
    framer = framer or Framer()
    if not enable_correction:
        for frame in framer.encode(data, enable_correction=enable_correction):
            for byte in frame:
                yield converter.to_bits[byte]
    else:
        for frame, frame_id in framer.encode(data, enable_correction=enable_correction):
            for byte in frame:
                yield converter.to_bits[byte], frame_id


@chain_wrapper
def _to_bytes(bits):
    converter = BitPacker()
    for chunk in common.iterate(data=bits, size=8,
                                func=tuple, truncate=True):
        yield [converter.to_byte[chunk]]


def decode_frames(bits, framer=None, enable_correction=False, raise_err=True):
    framer = framer or Framer()
    if not enable_correction:
        for frame in framer.decode(_to_bytes(bits), enable_correction=enable_correction, raise_err=raise_err):
            yield bytes(frame)
    else:
        for frame, frame_id in framer.decode(_to_bytes(bits), enable_correction=enable_correction, raise_err=raise_err):
            yield bytes(frame), frame_id
