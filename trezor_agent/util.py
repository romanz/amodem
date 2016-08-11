"""Various I/O and serialization utilities."""
import binascii
import contextlib
import hashlib
import io
import logging
import re
import struct

log = logging.getLogger(__name__)


def send(conn, data):
    """Send data blob to connection socket."""
    conn.sendall(data)


def recv(conn, size):
    """
    Receive bytes from connection socket or stream.

    If size is struct.calcsize()-compatible format, use it to unpack the data.
    Otherwise, return the plain blob as bytes.
    """
    try:
        fmt = size
        size = struct.calcsize(fmt)
    except TypeError:
        fmt = None
    try:
        _read = conn.recv
    except AttributeError:
        _read = conn.read

    res = io.BytesIO()
    while size > 0:
        buf = _read(size)
        if not buf:
            raise EOFError
        size = size - len(buf)
        res.write(buf)
    res = res.getvalue()
    if fmt:
        return struct.unpack(fmt, res)
    else:
        return res


def read_frame(conn):
    """Read size-prefixed frame from connection."""
    size, = recv(conn, '>L')
    return recv(conn, size)


def bytes2num(s):
    """Convert MSB-first bytes to an unsigned integer."""
    res = 0
    for i, c in enumerate(reversed(bytearray(s))):
        res += c << (i * 8)
    return res


def num2bytes(value, size):
    """Convert an unsigned integer to MSB-first bytes with specified size."""
    res = []
    for _ in range(size):
        res.append(value & 0xFF)
        value = value >> 8
    assert value == 0
    return bytes(bytearray(list(reversed(res))))


def pack(fmt, *args):
    """Serialize MSB-first message."""
    return struct.pack('>' + fmt, *args)


def frame(*msgs):
    """Serialize MSB-first length-prefixed frame."""
    res = io.BytesIO()
    for msg in msgs:
        res.write(msg)
    msg = res.getvalue()
    return pack('L', len(msg)) + msg


def crc24(blob):
    """See https://tools.ietf.org/html/rfc4880#section-6.1 for details."""
    CRC24_INIT = 0x0B704CE
    CRC24_POLY = 0x1864CFB

    crc = CRC24_INIT
    for octet in bytearray(blob):
        crc ^= (octet << 16)
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= CRC24_POLY
    assert 0 <= crc < 0x1000000
    crc_bytes = struct.pack('>L', crc)
    assert crc_bytes[:1] == b'\x00'
    return crc_bytes[1:]


def bit(value, i):
    """Extract the i-th bit out of value."""
    return 1 if value & (1 << i) else 0


def low_bits(value, n):
    """Extract the lowest n bits out of value."""
    return value & ((1 << n) - 1)


def split_bits(value, *bits):
    """
    Split integer value into list of ints, according to `bits` list.

    For example, split_bits(0x1234, 4, 8, 4) == [0x1, 0x23, 0x4]
    """
    result = []
    for b in reversed(bits):
        mask = (1 << b) - 1
        result.append(value & mask)
        value = value >> b
    assert value == 0

    result.reverse()
    return result


def readfmt(stream, fmt):
    """Read and unpack an object from stream, using a struct format string."""
    size = struct.calcsize(fmt)
    blob = stream.read(size)
    return struct.unpack(fmt, blob)


def prefix_len(fmt, blob):
    """Prefix `blob` with its size, serialized using `fmt` format."""
    return struct.pack(fmt, len(blob)) + blob


def hexlify(blob):
    """Utility for consistent hexadecimal formatting."""
    return binascii.hexlify(blob).decode('ascii').upper()


class Reader(object):
    """Read basic type objects out of given stream."""

    def __init__(self, stream):
        """Create a non-capturing reader."""
        self.s = stream
        self._captured = None

    def readfmt(self, fmt):
        """Read a specified object, using a struct format string."""
        size = struct.calcsize(fmt)
        blob = self.read(size)
        obj, = struct.unpack(fmt, blob)
        return obj

    def read(self, size=None):
        """Read `size` bytes from stream."""
        blob = self.s.read(size)
        if size is not None and len(blob) < size:
            raise EOFError
        if self._captured:
            self._captured.write(blob)
        return blob

    @contextlib.contextmanager
    def capture(self, stream):
        """Capture all data read during this context."""
        self._captured = stream
        try:
            yield
        finally:
            self._captured = None


_identity_regexp = re.compile(''.join([
    '^'
    r'(?:(?P<proto>.*)://)?',
    r'(?:(?P<user>.*)@)?',
    r'(?P<host>.*?)',
    r'(?::(?P<port>\w*))?',
    r'(?P<path>/.*)?',
    '$'
]))


def string_to_identity(s, identity_type):
    """Parse string into Identity protobuf."""
    m = _identity_regexp.match(s)
    result = m.groupdict()
    log.debug('parsed identity: %s', result)
    kwargs = {k: v for k, v in result.items() if v}
    return identity_type(**kwargs)


def identity_to_string(identity):
    """Dump Identity protobuf into its string representation."""
    result = []
    if identity.proto:
        result.append(identity.proto + '://')
    if identity.user:
        result.append(identity.user + '@')
    result.append(identity.host)
    if identity.port:
        result.append(':' + identity.port)
    if identity.path:
        result.append(identity.path)
    return ''.join(result)


def get_bip32_address(identity, ecdh=False):
    """Compute BIP32 derivation address according to SLIP-0013/0017."""
    index = struct.pack('<L', identity.index)
    addr = index + identity_to_string(identity).encode('ascii')
    log.debug('address string: %r', addr)
    digest = hashlib.sha256(addr).digest()
    s = io.BytesIO(bytearray(digest))

    hardened = 0x80000000
    addr_0 = [13, 17][bool(ecdh)]
    address_n = [addr_0] + list(recv(s, '<LLLL'))
    return [(hardened | value) for value in address_n]
