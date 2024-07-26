import binascii
import functools
import itertools
import logging
import struct
from math import erfc

import numpy as np
import reedsolo

from . import common

log = logging.getLogger(__name__)

# 创建RS编码器
NUM_SYMBOLS = 32
rs_codec = reedsolo.RSCodec(NUM_SYMBOLS)  # number of ecc symbols (you can repair nsym/2 errors and nsym erasures.


def ber_mqam(snr_db, M):
    # 根据snr重新协商纠错数量
    # Convert SNR from dB to linear scale
    snr_linear = 10 ** (snr_db / 10.0)
    # Calculate BER for M-QAM
    ber = (2 * (np.sqrt(M) - 1) / (np.sqrt(M) * np.log2(M))) * \
          erfc(np.sqrt(3 * snr_linear / (2 * (M - 1))))
    return ber


def set_rs_codec(snr_db):
    global NUM_SYMBOLS
    global rs_codec


def encode_with_rs(data):
    # 确保数据是bytearray类型
    if not isinstance(data, bytearray):
        data = bytearray(data)
    # 编码数据
    encoded = rs_codec.encode(data)
    return encoded


def decode_with_rs(encoded_data):
    try:
        # 解码数据
        decoded, _, _ = rs_codec.decode(encoded_data)
        return decoded
    except reedsolo.ReedSolomonError as e:
        import traceback
        traceback.print_exc()
        return None


def encode_pack(data):
    return encode_with_rs(data)


def decode_pack(encoded_data, chunk_size):
    chunk = bytearray(itertools.islice(encoded_data, chunk_size))
    if len(chunk) < chunk_size:
        raise ValueError(f'Incomplete frame, length {len(chunk)} < {chunk_size}(required)')

    decoded = decode_with_rs(chunk)
    return iter(decoded)


def _checksum_func(x):
    return binascii.crc32(bytes(x))


class Checksum:
    fmt = '>L'  # unsigned longs (32-bit)
    size = struct.calcsize(fmt)

    def encode(self, payload):
        checksum = _checksum_func(payload)
        encoded = struct.pack(self.fmt, checksum) + payload
        return encoded

    def decode(self, data):
        received, = struct.unpack(self.fmt, bytes(data[:self.size]))
        payload = data[self.size:]
        expected = _checksum_func(payload)
        if received != expected:
            log.warning('Invalid checksum: %08x != %08x', received, expected)
            raise ValueError('Invalid checksum')
        log.debug('Good checksum: %08x', received)
        return payload


class Framer:
    chunk_size = 255
    unencrypted_size = chunk_size - NUM_SYMBOLS
    block_size = unencrypted_size - 1 - 4  # 1 bytes length, 4 bytes crc
    prefix_fmt = '>B'
    prefix_len = struct.calcsize(prefix_fmt)
    checksum = Checksum()

    EOF = b''

    def _pack(self, block, padded_size=None):
        frame = self.checksum.encode(block)
        packed = bytearray(struct.pack(self.prefix_fmt, len(frame)) + frame)

        if padded_size is not None:
            current_length = len(packed)
            if current_length > padded_size:
                raise ValueError(f"Packed data length ({current_length}) exceeds target length ({padded_size})")

            padding_length = padded_size - current_length
            packed.extend(b'\x00' * padding_length)
        packed = encode_pack(packed)
        return packed

    def encode(self, data):
        for block in common.iterate(data=data, size=self.block_size,
                                    func=bytearray, truncate=False):
            yield self._pack(block=block, padded_size=self.unencrypted_size)
        yield self._pack(block=self.EOF, padded_size=self.unencrypted_size)

    def decode(self, data):
        data = iter(data)
        while True:
            pack = decode_pack(data, self.chunk_size)
            length, = _take_fmt(pack, self.prefix_fmt)
            frame = _take_len(pack, length)
            block = self.checksum.decode(frame)
            if block == self.EOF:
                log.debug('EOF frame detected')
                return

            yield block


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
def encode(data, framer=None):
    converter = BitPacker()
    framer = framer or Framer()
    for frame in framer.encode(data):
        for byte in frame:
            yield converter.to_bits[byte]


@chain_wrapper
def _to_bytes(bits):
    converter = BitPacker()
    for chunk in common.iterate(data=bits, size=8,
                                func=tuple, truncate=True):
        yield [converter.to_byte[chunk]]


def decode_frames(bits, framer=None):
    framer = framer or Framer()
    for frame in framer.decode(_to_bytes(bits)):
        yield bytes(frame)
