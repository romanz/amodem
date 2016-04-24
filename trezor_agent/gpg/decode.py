"""Decoders for GPG v2 data structures."""
import binascii
import contextlib
import hashlib
import io
import logging
import struct

import ecdsa
import ed25519

from trezor_agent.util import num2bytes

log = logging.getLogger(__name__)


def bit(value, i):
    """Extract the i-th bit out of value."""
    return 1 if value & (1 << i) else 0


def low_bits(value, n):
    """Extract the lowest n bits out of value."""
    return value & ((1 << n) - 1)


def readfmt(stream, fmt):
    """Read and unpack an object from stream, using a struct format string."""
    size = struct.calcsize(fmt)
    blob = stream.read(size)
    return struct.unpack(fmt, blob)


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

length_types = {0: '>B', 1: '>H', 2: '>L'}


def parse_subpackets(s):
    """See https://tools.ietf.org/html/rfc4880#section-5.2.3.1 for details."""
    subpackets = []
    total_size = s.readfmt('>H')
    data = s.read(total_size)
    s = Reader(io.BytesIO(data))

    while True:
        try:
            subpacket_len = s.readfmt('B')
        except EOFError:
            break

        subpackets.append(s.read(subpacket_len))

    return subpackets


def parse_mpi(s):
    """See https://tools.ietf.org/html/rfc4880#section-3.2 for details."""
    bits = s.readfmt('>H')
    blob = bytearray(s.read(int((bits + 7) // 8)))
    return sum(v << (8 * i) for i, v in enumerate(reversed(blob)))


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
    return reversed(result)


def _parse_nist256p1_verifier(mpi):
    prefix, x, y = split_bits(mpi, 4, 256, 256)
    assert prefix == 4
    point = ecdsa.ellipticcurve.Point(curve=ecdsa.NIST256p.curve,
                                      x=x, y=y)
    vk = ecdsa.VerifyingKey.from_public_point(
        point=point, curve=ecdsa.curves.NIST256p,
        hashfunc=hashlib.sha256)

    def _nist256p1_verify(signature, digest):
        vk.verify_digest(signature=signature,
                         digest=digest,
                         sigdecode=lambda rs, order: rs)
    return _nist256p1_verify


def _parse_ed25519_verifier(mpi):
    prefix, value = split_bits(mpi, 8, 256)
    assert prefix == 0x40
    vk = ed25519.VerifyingKey(num2bytes(value, size=32))

    def _ed25519_verify(signature, digest):
        sig = b''.join(num2bytes(val, size=32)
                       for val in signature)
        vk.verify(sig, digest)
    return _ed25519_verify


SUPPORTED_CURVES = {
    b'\x2A\x86\x48\xCE\x3D\x03\x01\x07': _parse_nist256p1_verifier,
    b'\x2B\x06\x01\x04\x01\xDA\x47\x0F\x01': _parse_ed25519_verifier,
}


class Parser(object):
    """Parse GPG packets from a given stream."""

    def __init__(self, stream, to_hash=None):
        """Create an empty parser."""
        self.stream = stream
        self.packet_types = {
            2: self.signature,
            6: self.pubkey,
            11: self.literal,
            13: self.user_id,
        }
        self.to_hash = io.BytesIO()
        if to_hash:
            self.to_hash.write(to_hash)

    def __iter__(self):
        """Support iterative parsing of available GPG packets."""
        return self

    def literal(self, stream):
        """See https://tools.ietf.org/html/rfc4880#section-5.9 for details."""
        p = {'type': 'literal'}
        p['format'] = stream.readfmt('c')
        filename_len = stream.readfmt('B')
        p['filename'] = stream.read(filename_len)
        p['date'] = stream.readfmt('>L')
        with stream.capture(self.to_hash):
            p['content'] = stream.read()
        return p

    def signature(self, stream):
        """See https://tools.ietf.org/html/rfc4880#section-5.2 for details."""
        p = {'type': 'signature'}

        to_hash = io.BytesIO()
        with stream.capture(to_hash):
            p['version'] = stream.readfmt('B')
            p['sig_type'] = stream.readfmt('B')
            p['pubkey_alg'] = stream.readfmt('B')
            p['hash_alg'] = stream.readfmt('B')
            p['hashed_subpackets'] = parse_subpackets(stream)
        self.to_hash.write(to_hash.getvalue())

        # https://tools.ietf.org/html/rfc4880#section-5.2.4
        self.to_hash.write(b'\x04\xff' + struct.pack('>L', to_hash.tell()))
        data_to_sign = self.to_hash.getvalue()
        log.debug('hashing %d bytes for signature: %r',
                  len(data_to_sign), data_to_sign)
        digest = hashlib.sha256(data_to_sign).digest()

        p['unhashed_subpackets'] = parse_subpackets(stream)
        p['hash_prefix'] = stream.readfmt('2s')
        if p['hash_prefix'] != digest[:2]:
            log.warning('Bad hash prefix: %r (expected %r)',
                        digest[:2], p['hash_prefix'])
        else:
            p['digest'] = digest
        p['sig'] = (parse_mpi(stream), parse_mpi(stream))
        assert not stream.read()

        return p

    def pubkey(self, stream):
        """See https://tools.ietf.org/html/rfc4880#section-5.5 for details."""
        p = {'type': 'pubkey'}
        packet = io.BytesIO()
        with stream.capture(packet):
            p['version'] = stream.readfmt('B')
            p['created'] = stream.readfmt('>L')
            p['algo'] = stream.readfmt('B')

            # https://tools.ietf.org/html/rfc6637#section-11
            oid_size = stream.readfmt('B')
            oid = stream.read(oid_size)
            assert oid in SUPPORTED_CURVES
            parser = SUPPORTED_CURVES[oid]

            mpi = parse_mpi(stream)
            log.debug('mpi: %x (%d bits)', mpi, mpi.bit_length())
            p['verifier'] = parser(mpi)
            assert not stream.read()

        # https://tools.ietf.org/html/rfc4880#section-12.2
        packet_data = packet.getvalue()
        data_to_hash = (b'\x99' + struct.pack('>H', len(packet_data)) +
                        packet_data)
        p['key_id'] = hashlib.sha1(data_to_hash).digest()[-8:]
        log.debug('key ID: %s', binascii.hexlify(p['key_id']).decode('ascii'))
        self.to_hash.write(data_to_hash)

        return p

    def user_id(self, stream):
        """See https://tools.ietf.org/html/rfc4880#section-5.11 for details."""
        value = stream.read()
        self.to_hash.write(b'\xb4' + struct.pack('>L', len(value)))
        self.to_hash.write(value)
        return {'type': 'user_id', 'value': value}

    def __next__(self):
        """See https://tools.ietf.org/html/rfc4880#section-4.2 for details."""
        try:
            value = self.stream.readfmt('B')
        except EOFError:
            raise StopIteration

        log.debug('prefix byte: %02x', value)
        assert bit(value, 7) == 1
        assert bit(value, 6) == 0  # new format not supported yet

        tag = low_bits(value, 6)
        length_type = low_bits(tag, 2)
        tag = tag >> 2
        fmt = length_types[length_type]
        log.debug('length_type: %s', fmt)
        packet_size = self.stream.readfmt(fmt)
        log.debug('packet length: %d', packet_size)
        packet_data = self.stream.read(packet_size)
        packet_type = self.packet_types.get(tag)
        if packet_type:
            p = packet_type(Reader(io.BytesIO(packet_data)))
        else:
            raise ValueError('Unknown packet type: {}'.format(packet_type))
        p['tag'] = tag
        log.debug('packet "%s": %s', p['type'], p)
        return p

    next = __next__


def load_public_key(stream):
    """Parse and validate GPG public key from an input stream."""
    parser = Parser(Reader(stream))
    pubkey, userid, signature = list(parser)
    log.debug('loaded public key "%s"', userid['value'])
    verify_digest(pubkey=pubkey, digest=signature['digest'],
                  signature=signature['sig'], label='GPG public key')
    return pubkey


def verify_digest(pubkey, digest, signature, label):
    """Verify a digest signature from a specified public key."""
    verifier = pubkey['verifier']
    try:
        verifier(signature, digest)
        log.debug('%s is OK', label)
    except ecdsa.keys.BadSignatureError:
        log.error('Bad %s!', label)
        raise
