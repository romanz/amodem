"""GPG protocol utilities."""

import base64
import hashlib
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


class PublicKey(object):
    """GPG representation for public key packets."""

    def __init__(self, curve_name, created, verifying_key):
        """Contruct using a ECDSA VerifyingKey object."""
        self.curve_info = SUPPORTED_CURVES[curve_name]
        self.created = int(created)  # time since Epoch
        self.verifying_key = verifying_key
        self.algo_id = self.curve_info['algo_id']
        hex_key_id = util.hexlify(self.key_id())[-8:]
        self.desc = 'GPG public key {}/{}'.format(curve_name, hex_key_id)

    def data(self):
        """Data for packet creation."""
        header = struct.pack('>BLB',
                             4,             # version
                             self.created,  # creation
                             self.algo_id)  # public key algorithm ID
        oid = util.prefix_len('>B', self.curve_info['oid'])
        blob = self.curve_info['serialize'](self.verifying_key)
        return header + oid + blob

    def data_to_hash(self):
        """Data for digest computation."""
        return b'\x99' + util.prefix_len('>H', self.data())

    def _fingerprint(self):
        return hashlib.sha1(self.data_to_hash()).digest()

    def key_id(self):
        """Short (8 byte) GPG key ID."""
        return self._fingerprint()[-8:]

    def __repr__(self):
        """Short (8 hexadecimal digits) GPG key ID."""
        return self.desc

    __str__ = __repr__


def _split_lines(body, size):
    lines = []
    for i in range(0, len(body), size):
        lines.append(body[i:i+size] + '\n')
    return ''.join(lines)


def armor(blob, type_str):
    """See https://tools.ietf.org/html/rfc4880#section-6 for details."""
    head = '-----BEGIN PGP {}-----\nVersion: GnuPG v2\n\n'.format(type_str)
    body = base64.b64encode(blob).decode('ascii')
    checksum = base64.b64encode(util.crc24(blob)).decode('ascii')
    tail = '-----END PGP {}-----\n'.format(type_str)
    return head + _split_lines(body, 64) + '=' + checksum + '\n' + tail


def make_signature(signer_func, data_to_sign, public_algo,
                   hashed_subpackets, unhashed_subpackets, sig_type=0):
    """Create new GPG signature."""
    # pylint: disable=too-many-arguments
    header = struct.pack('>BBBB',
                         4,         # version
                         sig_type,  # rfc4880 (section-5.2.1)
                         public_algo,
                         8)         # hash_alg (SHA256)
    hashed = subpackets(*hashed_subpackets)
    unhashed = subpackets(*unhashed_subpackets)
    tail = b'\x04\xff' + struct.pack('>L', len(header) + len(hashed))
    data_to_hash = data_to_sign + header + hashed + tail

    log.debug('hashing %d bytes', len(data_to_hash))
    digest = hashlib.sha256(data_to_hash).digest()
    log.debug('signing digest: %s', util.hexlify(digest))
    sig = signer_func(digest=digest)

    return bytes(header + hashed + unhashed +
                 digest[:2] +  # used for decoder's sanity check
                 sig)  # actual ECDSA signature
