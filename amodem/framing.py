import binascii
import functools
import itertools
import logging
import struct

from . import common

log = logging.getLogger(__name__)


def _checksum_func(x):
    """ The result will be unsigned on Python 2/3. """
    return binascii.crc32(bytes(x)) & 0xFFFFFFFF


def _short_checksum_func(x):
    """ The result will be unsigned on Python 2/3. """
    return binascii.crc32(bytes(x)) & 0xFF


class StopOnFault:
    """ error codes for fault tolerance -
    matching this code will raise error of this type """

    PAYLOAD_ERR = 0x01
    HEADER_ERR = 0x02
    SEQUENCE_ERR = 0x04
    ALL_ERR = 0xFF  # halt on all error
    helpMsg = """Payload_error: 0x01 / Header_err: 0x02 / sequence_err=0x04 """


class Checksum:
    fmt = ">L"  # unsigned longs (32-bit)
    size = struct.calcsize(fmt)

    def __init__(self, stopOnCode=0):
        self.fTOL = stopOnCode

    def encode(self, payload):
        checksum = _checksum_func(payload)
        return struct.pack(self.fmt, checksum) + payload

    def decode(self, data, cnt=0):
        (received,) = struct.unpack(self.fmt, bytes(data[: self.size]))
        payload = data[self.size:]
        expected = _checksum_func(payload)
        if received != expected:
            errMSG = "Frame %d %s checksum: %02x != calc checksum: %02x " % (
                cnt,
                "Payload",
                received,
                expected,
            )
            log.warning(errMSG)
            if bool(self.fTOL & StopOnFault.PAYLOAD_ERR):
                raise ValueError(errMSG)
        log.debug("Good checksum: %08x", received)
        return payload


class Framer:
    """ Class for handling data frames
     packing, unpacking, checksums, etc """

    prefix_fmt = ">LBHB"
    prefix_len = struct.calcsize(prefix_fmt)

    EOF = b""

    def __init__(self, flags=0, stopOnCode=StopOnFault.ALL_ERR,
                 block_size=250):
        self.flags = flags
        self.fTOL = stopOnCode
        self.checksum = Checksum(stopOnCode=stopOnCode)
        self.block_size = block_size

    def _pack(self, block, flags=0, cnt=0):
        frame = self.checksum.encode(block)
        prefix = struct.pack(self.prefix_fmt[:-1], cnt, flags, len(frame))
        return bytearray(
            prefix + struct.pack(">B", _short_checksum_func(prefix)) + frame
        )

    def encode(self, data):
        idx = -1
        for idx, block in enumerate(common.iterate(
                data=data, size=self.block_size, func=bytearray,
                truncate=False)):
            yield self._pack(block=block, flags=self.flags, cnt=idx)
        yield self._pack(block=self.EOF, flags=self.flags, cnt=idx + 1)

    def decode(self, data):
        data = iter(data)
        local_cnt = 0
        prior_cnt = -1
        prior_len = -1
        while True:
            cnt, flag, length, mychecksum = _take_fmt(
                data, self.prefix_fmt, local_cnt, self.fTOL
            )
            pre_chk = _short_checksum_func(
                struct.pack(self.prefix_fmt[:-1], cnt, flag, length)
            )
            if pre_chk != mychecksum:
                errMSG = "Frame %d %s checksum:%02x != calc checksum:%02x" % (
                    cnt,
                    "Header",
                    mychecksum,
                    pre_chk,
                )
                log.warning(errMSG)
                if bool(self.fTOL & StopOnFault.HEADER_ERR):
                    raise ValueError(errMSG)

            if cnt != local_cnt or (prior_cnt >= 0 and cnt != prior_cnt + 1):
                errMSG = "Frame %d %s error. Msg cnt %d, Prior Msg cnt %d" % (
                    local_cnt,
                    "Sequence counting",
                    cnt,
                    prior_cnt,
                )
                log.warning(errMSG)
                if bool(self.fTOL & StopOnFault.SEQUENCE_ERR):
                    raise ValueError(errMSG)
                if length != prior_len:
                    length = prior_len  # guessing what length should be
            frame = _take_len(data, length, local_cnt, self.fTOL)
            block = self.checksum.decode(frame, local_cnt)
            if block == self.EOF:
                log.debug("EOF frame detected")
                return
            prior_cnt = cnt
            prior_len = length
            local_cnt += 1
            yield block


def _take_fmt(data, fmt, cnt=0, fTOL=StopOnFault.ALL_ERR):
    length = struct.calcsize(fmt)
    chunk = bytearray(itertools.islice(data, length))
    if len(chunk) < length:
        errMSG = "Frame: %d - Data truncated in %s" % (cnt, "prefix")
        log.error(errMSG)
        if bool(fTOL & StopOnFault.HEADER_ERR):
            raise ValueError(errMSG)
        return struct.unpack(fmt, bytes([0]) * length)
    return struct.unpack(fmt, bytes(chunk))


def _take_len(data, length, cnt=0, fTOL=StopOnFault.ALL_ERR):
    chunk = bytearray(itertools.islice(data, length))
    if len(chunk) < length:
        errMSG = "Frame: %d - Data truncated in %s" % (cnt, "payload")
        log.warning(errMSG)
        if bool(fTOL & StopOnFault.PAYLOAD_ERR):
            raise ValueError(errMSG)
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
def encode(data, framer=None, flags=0, block_size=250):
    converter = BitPacker()
    framer = framer or Framer(flags=flags, block_size=block_size)
    for frame in framer.encode(data):
        for byte in frame:
            yield converter.to_bits[byte]


@chain_wrapper
def _to_bytes(bits):
    converter = BitPacker()
    for chunk in common.iterate(data=bits, size=8, func=tuple, truncate=True):
        yield [converter.to_byte[chunk]]


def decode_frames(bits, framer=None, stopOnCode=StopOnFault.ALL_ERR,
                  block_size=250):
    """ Decodes frames from bitstream """
    framer = framer or Framer(stopOnCode=stopOnCode, block_size=block_size)
    for frame in framer.decode(_to_bytes(bits)):
        yield bytes(frame)
