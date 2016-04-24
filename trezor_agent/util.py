"""Various I/O and serialization utilities."""
import io
import struct


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
    assert crc_bytes[0] == b'\x00'
    return crc_bytes[1:]
