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
    return 1 if value & (1 << i) else 0


def low_bits(value, n):
    return value & ((1 << n) - 1)


def readfmt(stream, fmt):
    size = struct.calcsize(fmt)
    blob = stream.read(size)
    return struct.unpack(fmt, blob)


class Reader(object):
    def __init__(self, stream):
        self.s = stream
        self._captured = None

    def readfmt(self, fmt):
        size = struct.calcsize(fmt)
        blob = self.read(size)
        obj, = struct.unpack(fmt, blob)
        return obj

    def read(self, size=None):
        blob = self.s.read(size)
        if size is not None and len(blob) < size:
            raise EOFError
        if self._captured:
            self._captured.write(blob)
        return blob

    @contextlib.contextmanager
    def capture(self, stream):
        self._captured = stream
        try:
            yield
        finally:
            self._captured = None

length_types = {0: '>B', 1: '>H', 2: '>L'}


def parse_subpackets(s):
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
    bits = s.readfmt('>H')
    blob = bytearray(s.read(int((bits + 7) // 8)))
    return sum(v << (8 * i) for i, v in enumerate(reversed(blob)))


def split_bits(value, *bits):
    result = []
    for b in reversed(bits):
        mask = (1 << b) - 1
        result.append(value & mask)
        value = value >> b
    assert value == 0
    return reversed(result)

SUPPORTED_CURVES = {
    b'\x2A\x86\x48\xCE\x3D\x03\x01\x07': 'nist256p1',
    b'\x2B\x06\x01\x04\x01\xDA\x47\x0F\x01': 'ed25519',
}

class Parser(object):
    def __init__(self, stream, to_hash=None):
        self.stream = stream
        self.packet_types = {
            2: self.signature,
            4: self.onepass,
            6: self.pubkey,
            11: self.literal,
            13: self.user_id,
        }
        self.to_hash = io.BytesIO()
        if to_hash:
            self.to_hash.write(to_hash)

    def __iter__(self):
        return self

    def onepass(self, stream):
        # pylint: disable=no-self-use
        p = {'type': 'onepass'}
        p['version'] = stream.readfmt('B')
        p['sig_type'] = stream.readfmt('B')
        p['hash_alg'] = stream.readfmt('B')
        p['pubkey_alg'] = stream.readfmt('B')
        p['key_id'] = stream.readfmt('8s')
        p['nested'] = stream.readfmt('B')
        assert not stream.read()
        return p

    def literal(self, stream):
        p = {'type': 'literal'}
        p['format'] = stream.readfmt('c')
        filename_len = stream.readfmt('B')
        p['filename'] = stream.read(filename_len)
        p['date'] = stream.readfmt('>L')
        with stream.capture(self.to_hash):
            p['content'] = stream.read()
        return p

    def signature(self, stream):
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
            curve_name = SUPPORTED_CURVES[oid]

            mpi = parse_mpi(stream)
            log.debug('mpi: %x (%d bits)', mpi, mpi.bit_length())
            if curve_name == 'nist256p1':
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
                p['verifier'] = _nist256p1_verify
            elif curve_name == 'ed25519':
                prefix, value  = split_bits(mpi, 8, 256)
                assert prefix == 0x40
                vk = ed25519.VerifyingKey(num2bytes(value, size=32))

                def _ed25519_verify(signature, digest):
                    sig = b''.join(num2bytes(val, size=32)
                                   for val in signature)
                    vk.verify(sig, digest)
                p['verifier'] = _ed25519_verify
            else:
                raise ValueError('unsupported curve {}'.format(curve_name))

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
        value = stream.read()
        self.to_hash.write(b'\xb4' + struct.pack('>L', len(value)))
        self.to_hash.write(value)
        return {'type': 'user_id', 'value': value}

    def __next__(self):
        try:
            # https://tools.ietf.org/html/rfc4880#section-4.2
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
            p = {'type': 'UNKNOWN'}
        p['tag'] = tag
        log.debug('packet "%s": %s', p['type'], p)
        return p

    next = __next__


def load_public_key(stream):
    parser = Parser(Reader(stream))
    pubkey, userid, signature = list(parser)
    log.debug('loaded public key "%s"', userid['value'])
    verify_digest(pubkey=pubkey, digest=signature['digest'],
                  signature=signature['sig'], label='GPG public key')
    return pubkey


def verify_digest(pubkey, digest, signature, label):
    verifier = pubkey['verifier']
    try:
        verifier(signature, digest)
        log.debug('%s is OK', label)
    except ecdsa.keys.BadSignatureError:
        log.error('Bad %s!', label)
        raise
