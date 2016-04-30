"""GPG protocol utilities."""

import logging
import struct

from .. import formats, util

log = logging.getLogger(__name__)


def packet(tag, blob):
    """Create small GPG packet."""
    assert len(blob) < 2**32

    if len(blob) < 2**8:
        length_type = 0
    elif len(blob) < 2**16:
        length_type = 1
    else:
        length_type = 2

    fmt = ['>B', '>H', '>L'][length_type]
    leading_byte = 0x80 | (tag << 2) | (length_type)
    return struct.pack('>B', leading_byte) + util.prefix_len(fmt, blob)


def subpacket(subpacket_type, fmt, *values):
    """Create GPG subpacket."""
    blob = struct.pack(fmt, *values) if values else fmt
    return struct.pack('>B', subpacket_type) + blob


def subpacket_long(subpacket_type, value):
    """Create GPG subpacket with 32-bit unsigned integer."""
    return subpacket(subpacket_type, '>L', value)


def subpacket_time(value):
    """Create GPG subpacket with time in seconds (since Epoch)."""
    return subpacket_long(2, value)


def subpacket_byte(subpacket_type, value):
    """Create GPG subpacket with 8-bit unsigned integer."""
    return subpacket(subpacket_type, '>B', value)


def subpackets(*items):
    """Serialize several GPG subpackets."""
    prefixed = [util.prefix_len('>B', item) for item in items]
    return util.prefix_len('>H', b''.join(prefixed))


def mpi(value):
    """Serialize multipresicion integer using GPG format."""
    bits = value.bit_length()
    data_size = (bits + 7) // 8
    data_bytes = bytearray(data_size)
    for i in range(data_size):
        data_bytes[i] = value & 0xFF
        value = value >> 8

    data_bytes.reverse()
    return struct.pack('>H', bits) + bytes(data_bytes)


def _serialize_nist256(vk):
    return mpi((4 << 512) |
               (vk.pubkey.point.x() << 256) |
               (vk.pubkey.point.y()))


def _serialize_ed25519(vk):
    return mpi((0x40 << 256) |
               util.bytes2num(vk.to_bytes()))


SUPPORTED_CURVES = {
    formats.CURVE_NIST256: {
        # https://tools.ietf.org/html/rfc6637#section-11
        'oid': b'\x2A\x86\x48\xCE\x3D\x03\x01\x07',
        'algo_id': 19,
        'serialize': _serialize_nist256
    },
    formats.CURVE_ED25519: {
        'oid': b'\x2B\x06\x01\x04\x01\xDA\x47\x0F\x01',
        'algo_id': 22,
        'serialize': _serialize_ed25519
    }
}


CUSTOM_SUBPACKET = subpacket(100, b'TREZOR-GPG')  # marks "our" pubkey


def find_curve_by_algo_id(algo_id):
    """Find curve name that matches a public key algorith ID."""
    curve_name, = [name for name, info in SUPPORTED_CURVES.items()
                   if info['algo_id'] == algo_id]
    return curve_name
