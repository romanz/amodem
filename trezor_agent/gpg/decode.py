"""Decoders for GPG v2 data structures."""
import base64
import functools
import hashlib
import io
import logging
import struct

import ecdsa
import ed25519

from . import proto
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


def parse_mpis(s, n):
    """Parse multiple MPIs from stream."""
    return [parse_mpi(s) for _ in range(n)]


def _parse_nist256p1_verifier(mpi):
    prefix, x, y = util.split_bits(mpi, 4, 256, 256)
    assert prefix == 4
    point = ecdsa.ellipticcurve.Point(curve=ecdsa.NIST256p.curve,
                                      x=x, y=y)
    vk = ecdsa.VerifyingKey.from_public_point(
        point=point, curve=ecdsa.curves.NIST256p,
        hashfunc=hashlib.sha256)

    def _nist256p1_verify(signature, digest):
        result = vk.verify_digest(signature=signature,
                                  digest=digest,
                                  sigdecode=lambda rs, order: rs)
        log.debug('nist256p1 ECDSA signature is OK (%s)', result)
    return _nist256p1_verify, vk


def _parse_ed25519_verifier(mpi):
    prefix, value = util.split_bits(mpi, 8, 256)
    assert prefix == 0x40
    vk = ed25519.VerifyingKey(util.num2bytes(value, size=32))

    def _ed25519_verify(signature, digest):
        sig = b''.join(util.num2bytes(val, size=32)
                       for val in signature)
        result = vk.verify(sig, digest)
        log.debug('ed25519 ECDSA signature is OK (%s)', result)
    return _ed25519_verify, vk


def _create_rsa_verifier(n, e):
    def verifier(signature, digest):
        s, = signature
        size = n.bit_length()
        result = pow(s, e, n) % (2 ** 256)
        digest = util.bytes2num(digest)
        if result == digest:
            log.debug('RSA-%d signature is OK', size)
            return True
        else:
            raise ValueError('invalid RSA signature')

    return verifier

SUPPORTED_CURVES = {
    b'\x2A\x86\x48\xCE\x3D\x03\x01\x07': _parse_nist256p1_verifier,
    b'\x2B\x06\x01\x04\x01\xDA\x47\x0F\x01': _parse_ed25519_verifier,
}

RSA_ALGO_IDS = {1, 2, 3}
ELGAMAL_ALGO_ID = 16
DSA_ALGO_ID = 17
ECDSA_ALGO_IDS = {18, 19, 22}  # {ecdsa, nist256, ed25519}


def _parse_literal(stream):
    """See https://tools.ietf.org/html/rfc4880#section-5.9 for details."""
    p = {'type': 'literal'}
    p['format'] = stream.readfmt('c')
    filename_len = stream.readfmt('B')
    p['filename'] = stream.read(filename_len)
    p['date'] = stream.readfmt('>L')
    p['content'] = stream.read()
    p['_to_hash'] = p['content']
    return p


def _parse_embedded_signatures(subpackets):
    for packet in subpackets:
        data = bytearray(packet)
        if data[0] == 32:
            # https://tools.ietf.org/html/rfc4880#section-5.2.3.26
            stream = io.BytesIO(data[1:])
            yield _parse_signature(util.Reader(stream))


def _parse_signature(stream):
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
    embedded = list(_parse_embedded_signatures(p['unhashed_subpackets']))
    if embedded:
        log.debug('embedded sigs: %s', embedded)
        p['embedded'] = embedded

    p['_is_custom'] = (proto.CUSTOM_SUBPACKET in p['unhashed_subpackets'])

    p['hash_prefix'] = stream.readfmt('2s')
    if p['pubkey_alg'] in ECDSA_ALGO_IDS:
        p['sig'] = (parse_mpi(stream), parse_mpi(stream))
    elif p['pubkey_alg'] in RSA_ALGO_IDS:  # RSA
        p['sig'] = (parse_mpi(stream),)
    elif p['pubkey_alg'] == DSA_ALGO_ID:
        p['sig'] = (parse_mpi(stream), parse_mpi(stream))
    else:
        log.error('unsupported public key algo: %d', p['pubkey_alg'])

    assert not stream.read()
    return p


def _parse_pubkey(stream, packet_type='pubkey'):
    """See https://tools.ietf.org/html/rfc4880#section-5.5 for details."""
    p = {'type': packet_type}
    packet = io.BytesIO()
    with stream.capture(packet):
        p['version'] = stream.readfmt('B')
        p['created'] = stream.readfmt('>L')
        p['algo'] = stream.readfmt('B')
        if p['algo'] in ECDSA_ALGO_IDS:
            log.debug('parsing elliptic curve key')
            # https://tools.ietf.org/html/rfc6637#section-11
            oid_size = stream.readfmt('B')
            oid = stream.read(oid_size)
            assert oid in SUPPORTED_CURVES, util.hexlify(oid)
            parser = SUPPORTED_CURVES[oid]

            mpi = parse_mpi(stream)
            log.debug('mpi: %x (%d bits)', mpi, mpi.bit_length())
            p['verifier'], p['verifying_key'] = parser(mpi)
            leftover = stream.read()
            if leftover:
                leftover = io.BytesIO(leftover)
                # https://tools.ietf.org/html/rfc6637#section-8
                # should be b'\x03\x01\x08\x07': SHA256 + AES128
                size, = util.readfmt(leftover, 'B')
                p['kdf'] = leftover.read(size)
                assert not leftover.read()
        elif p['algo'] == DSA_ALGO_ID:
            log.warning('DSA signatures are not verified')
            parse_mpis(stream, n=4)
        elif p['algo'] == ELGAMAL_ALGO_ID:
            log.warning('ElGamal signatures are not verified')
            parse_mpis(stream, n=3)
        else:  # assume RSA
            log.debug('parsing RSA key')
            n, e = parse_mpis(stream, n=2)
            p['verifier'] = _create_rsa_verifier(n, e)
            assert not stream.read()

    # https://tools.ietf.org/html/rfc4880#section-12.2
    packet_data = packet.getvalue()
    data_to_hash = (b'\x99' + struct.pack('>H', len(packet_data)) +
                    packet_data)
    p['key_id'] = hashlib.sha1(data_to_hash).digest()[-8:]
    p['_to_hash'] = data_to_hash
    log.debug('key ID: %s', util.hexlify(p['key_id']))
    return p

_parse_subkey = functools.partial(_parse_pubkey, packet_type='subkey')


def _parse_user_id(stream):
    """See https://tools.ietf.org/html/rfc4880#section-5.11 for details."""
    value = stream.read()
    to_hash = b'\xb4' + util.prefix_len('>L', value)
    return {'type': 'user_id', 'value': value, '_to_hash': to_hash}


PACKET_TYPES = {
    2: _parse_signature,
    6: _parse_pubkey,
    11: _parse_literal,
    13: _parse_user_id,
    14: _parse_subkey,
}


def parse_packets(stream):
    """
    Support iterative parsing of available GPG packets.

    See https://tools.ietf.org/html/rfc4880#section-4.2 for details.
    """
    while True:
        try:
            value = stream.readfmt('B')
        except EOFError:
            return

        log.debug('prefix byte: %s', bin(value))
        assert util.bit(value, 7) == 1
        assert util.bit(value, 6) == 0  # new format not supported yet

        tag = util.low_bits(value, 6)
        length_type = util.low_bits(tag, 2)
        tag = tag >> 2
        fmt = {0: '>B', 1: '>H', 2: '>L'}[length_type]
        packet_size = stream.readfmt(fmt)

        log.debug('packet length: %d', packet_size)
        packet_data = stream.read(packet_size)
        packet_type = PACKET_TYPES.get(tag)
        assert packet_type is not None, tag

        p = packet_type(util.Reader(io.BytesIO(packet_data)))
        p['tag'] = tag
        log.debug('packet "%s": %s', p['type'], p)
        yield p


def digest_packets(packets):
    """Compute digest on specified packets, according to '_to_hash' field."""
    data_to_hash = io.BytesIO()
    for p in packets:
        data_to_hash.write(p['_to_hash'])
    return hashlib.sha256(data_to_hash.getvalue()).digest()


def load_public_key(pubkey_bytes, use_custom=False):
    """Parse and validate GPG public key from an input stream."""
    stream = io.BytesIO(pubkey_bytes)
    packets = list(parse_packets(util.Reader(stream)))
    pubkey, userid, signature = packets[:3]
    packets = packets[3:]

    digest = digest_packets([pubkey, userid, signature])
    assert signature['hash_prefix'] == digest[:2]
    log.debug('loaded public key "%s"', userid['value'])
    if pubkey.get('verifier'):
        verify_digest(pubkey=pubkey, digest=digest,
                      signature=signature['sig'], label='GPG public key')
    else:
        log.warning('public key %s cannot be verified!',
                    util.hexlify(pubkey['key_id']))

    packet = pubkey
    while use_custom:
        if packet['type'] in ('pubkey', 'subkey') and signature['_is_custom']:
            log.debug('found custom %s', packet['type'])
            break

        packet, signature = packets[:2]
        packets = packets[2:]

    packet['user_id'] = userid['value']
    return packet


def load_signature(stream, original_data):
    """Load signature from stream, and compute GPG digest for verification."""
    signature, = list(parse_packets(util.Reader(stream)))
    digest = digest_packets([{'_to_hash': original_data}, signature])
    assert signature['hash_prefix'] == digest[:2]
    return signature, digest


def verify_digest(pubkey, digest, signature, label):
    """Verify a digest signature from a specified public key."""
    verifier = pubkey['verifier']
    try:
        verifier(signature, digest)
        log.debug('%s is OK', label)
    except ecdsa.keys.BadSignatureError:
        log.error('Bad %s!', label)
        raise ValueError('Invalid ECDSA signature for {}'.format(label))


def remove_armor(armored_data):
    """Decode armored data into its binary form."""
    stream = io.BytesIO(armored_data)
    lines = stream.readlines()[3:-1]
    data = base64.b64decode(b''.join(lines))
    payload, checksum = data[:-3], data[-3:]
    assert util.crc24(payload) == checksum
    return payload


def verify(pubkey, signature, original_data):
    """Verify correctness of public key and signature."""
    stream = io.BytesIO(remove_armor(signature))
    signature, digest = load_signature(stream, original_data)
    verify_digest(pubkey=pubkey, digest=digest,
                  signature=signature['sig'], label='GPG signature')
