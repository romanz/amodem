"""Decoders for GPG v2 data structures."""
import hashlib
import io
import logging
import struct
import subprocess

import ecdsa
import ed25519

from .. import util

log = logging.getLogger(__name__)


def parse_subpackets(s):
    """See https://tools.ietf.org/html/rfc4880#section-5.2.3.1 for details."""
    subpackets = []
    total_size = s.readfmt('>H')
    data = s.read(total_size)
    s = util.Reader(io.BytesIO(data))

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


def _parse_nist256p1_verifier(mpi):
    prefix, x, y = util.split_bits(mpi, 4, 256, 256)
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
    prefix, value = util.split_bits(mpi, 8, 256)
    assert prefix == 0x40
    vk = ed25519.VerifyingKey(util.num2bytes(value, size=32))

    def _ed25519_verify(signature, digest):
        sig = b''.join(util.num2bytes(val, size=32)
                       for val in signature)
        vk.verify(sig, digest)
    return _ed25519_verify


SUPPORTED_CURVES = {
    b'\x2A\x86\x48\xCE\x3D\x03\x01\x07': _parse_nist256p1_verifier,
    b'\x2B\x06\x01\x04\x01\xDA\x47\x0F\x01': _parse_ed25519_verifier,
}


class Parser(object):
    """Parse GPG packets from a given stream."""

    def __init__(self, stream):
        """Create an empty parser."""
        self.stream = stream
        self.packet_types = {
            2: self.signature,
            6: self.pubkey,
            11: self.literal,
            13: self.user_id,
        }

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
        p['content'] = stream.read()
        p['_to_hash'] = p['content']
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

        # https://tools.ietf.org/html/rfc4880#section-5.2.4
        tail_to_hash = b'\x04\xff' + struct.pack('>L', to_hash.tell())

        p['_to_hash'] = to_hash.getvalue() + tail_to_hash

        p['unhashed_subpackets'] = parse_subpackets(stream)
        p['hash_prefix'] = stream.readfmt('2s')
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
        p['_to_hash'] = data_to_hash
        log.debug('key ID: %s', util.hexlify(p['key_id']))

        return p

    def user_id(self, stream):
        """See https://tools.ietf.org/html/rfc4880#section-5.11 for details."""
        value = stream.read()
        to_hash = b'\xb4' + util.prefix_len('>L', value)
        return {'type': 'user_id', 'value': value, '_to_hash': to_hash}

    def __next__(self):
        """See https://tools.ietf.org/html/rfc4880#section-4.2 for details."""
        try:
            value = self.stream.readfmt('B')
        except EOFError:
            raise StopIteration

        log.debug('prefix byte: %02x', value)
        assert util.bit(value, 7) == 1
        assert util.bit(value, 6) == 0  # new format not supported yet

        tag = util.low_bits(value, 6)
        length_type = util.low_bits(tag, 2)
        tag = tag >> 2
        fmt = {0: '>B', 1: '>H', 2: '>L'}[length_type]
        log.debug('length_type: %s', fmt)
        packet_size = self.stream.readfmt(fmt)
        log.debug('packet length: %d', packet_size)
        packet_data = self.stream.read(packet_size)
        packet_type = self.packet_types.get(tag)
        if packet_type:
            p = packet_type(util.Reader(io.BytesIO(packet_data)))
        else:
            raise ValueError('Unknown packet type: {}'.format(tag))
        p['tag'] = tag
        log.debug('packet "%s": %s', p['type'], p)
        return p

    next = __next__


def digest_packets(packets):
    data_to_hash = io.BytesIO()
    for p in packets:
        data_to_hash.write(p['_to_hash'])
    return hashlib.sha256(data_to_hash.getvalue()).digest()


def load_public_key(stream):
    """Parse and validate GPG public key from an input stream."""
    parser = Parser(util.Reader(stream))
    pubkey, userid, signature = list(parser)
    digest = digest_packets([pubkey, userid, signature])
    assert signature['hash_prefix'] == digest[:2]
    log.debug('loaded public key "%s"', userid['value'])
    verify_digest(pubkey=pubkey, digest=digest,
                  signature=signature['sig'], label='GPG public key')
    return pubkey

def load_signature(stream, original_data):
    parser = Parser(util.Reader(stream))
    signature, = parser
    digest = digest_packets([{'_to_hash': original_data}, signature])
    assert signature['hash_prefix'] == digest[:2]
    return signature, digest


def load_from_gpg(user_id):
    """Load existing GPG public key for `user_id` from local keyring."""
    pubkey_bytes = subprocess.check_output(['gpg2', '--export', user_id])
    if pubkey_bytes:
        return load_public_key(io.BytesIO(pubkey_bytes))
    else:
        log.error('could not find public key %r in local GPG keyring', user_id)
        raise KeyError(user_id)


def verify_digest(pubkey, digest, signature, label):
    """Verify a digest signature from a specified public key."""
    verifier = pubkey['verifier']
    try:
        verifier(signature, digest)
        log.debug('%s is OK', label)
    except ecdsa.keys.BadSignatureError:
        log.error('Bad %s!', label)
        raise
