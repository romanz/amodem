import struct
import io


def send(conn, data, fmt=None):
    if fmt:
        data = struct.pack(fmt, *data)
    conn.sendall(data)


def recv(conn, size):
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
    size, = recv(conn, '>L')
    return recv(conn, size)


def bytes2num(s):
    res = 0
    for i, c in enumerate(reversed(bytearray(s))):
        res += c << (i * 8)
    return res


def num2bytes(value, size):
    res = []
    for _ in range(size):
        res.append(value & 0xFF)
        value = value >> 8
    assert value == 0
    return bytearray(list(reversed(res)))


def pack(fmt, *args):
    return struct.pack('>' + fmt, *args)


def frame(*msgs):
    res = io.BytesIO()
    for msg in msgs:
        res.write(msg)
    msg = res.getvalue()
    return pack('L', len(msg)) + msg
