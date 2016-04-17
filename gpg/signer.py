#!/usr/bin/env python
import argparse
import base64
import binascii
import hashlib
import logging
import struct
import time

import ecdsa

import trezor_agent.client
import trezor_agent.formats
import trezor_agent.util
import util

log = logging.getLogger(__name__)


def prefix_len(fmt, blob):
    return struct.pack(fmt, len(blob)) + blob


def packet(tag, blob):
    assert len(blob) < 256
    length_type = 0  # : 1 byte for length
    leading_byte = 0x80 | (tag << 2) | (length_type)
    return struct.pack('>B', leading_byte) + prefix_len('>B', blob)


def subpacket(subpacket_type, fmt, *values):
    blob = struct.pack(fmt, *values) if values else fmt
    return struct.pack('>B', subpacket_type) + blob


def subpacket_long(subpacket_type, value):
    return subpacket(subpacket_type, '>L', value)


def subpacket_time(value):
    return subpacket_long(2, value)


def subpacket_byte(subpacket_type, value):
    return subpacket(subpacket_type, '>B', value)


def subpackets(*items):
    prefixed = [prefix_len('>B', item) for item in items]
    return prefix_len('>H', b''.join(prefixed))


def mpi(value):
    bits = value.bit_length()
    data_size = (bits + 7) // 8
    data_bytes = [0] * data_size
    for i in range(data_size):
        data_bytes[i] = value & 0xFF
        value = value >> 8

    data_bytes.reverse()
    return struct.pack('>H', bits) + bytearray(data_bytes)


def time_format(t):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))


def hexlify(blob):
    return binascii.hexlify(blob).decode('ascii').upper()


def split_lines(body, size):
    lines = []
    for i in range(0, len(body), size):
        lines.append(body[i:i+size] + '\n')
    return ''.join(lines)


def armor_sig(blob):
    head = '-----BEGIN PGP SIGNATURE-----\nVersion: GnuPG v2\n\n'
    body = base64.b64encode(blob)
    checksum = base64.b64encode(util.crc24(blob))
    tail = '-----END PGP SIGNATURE-----\n'
    return head + split_lines(body + '=' + checksum, 64) + tail


class Signer(object):

    curve = ecdsa.NIST256p
    ecdsa_curve_name = trezor_agent.formats.CURVE_NIST256

    def __init__(self, user_id, created):
        self.user_id = user_id
        self.client_wrapper = trezor_agent.factory.load()

        # This requires the following patch to trezor-mcu to work:
        # https://gist.github.com/romanz/b66f5df1ca8ef15641df8ea5bb09fd47
        self.identity = self.client_wrapper.identity_type()
        self.identity.proto = 'gpg'
        self.identity.host = user_id
        addr = trezor_agent.client.get_address(self.identity)
        public_node = self.client_wrapper.connection.get_public_node(
            n=addr, ecdsa_curve_name=self.ecdsa_curve_name)

        verifying_key = trezor_agent.formats.decompress_pubkey(
            pubkey=public_node.node.public_key,
            curve_name=self.ecdsa_curve_name)

        self.created = int(created)
        header = struct.pack('>BLB',
                             4,             # version
                             self.created,  # creation
                             19)            # ECDSA

        # https://tools.ietf.org/html/rfc6637#section-11  (NIST P-256 OID)
        oid = prefix_len('>B', b'\x2A\x86\x48\xCE\x3D\x03\x01\x07')

        point = verifying_key.pubkey.point
        self.pubkey_data = header + oid + mpi((4 << 512) |
                                              (point.x() << 256) |
                                              (point.y()))

        self.data_to_hash = b'\x99' + prefix_len('>H', self.pubkey_data)
        fingerprint = hashlib.sha1(self.data_to_hash).digest()
        self.key_id = fingerprint[-8:]
        log.info('key %s created at %s',
                 hexlify(fingerprint[-4:]), time_format(self.created))

    def close(self):
        self.client_wrapper.connection.clear_session()
        self.client_wrapper.connection.close()

    def export(self):
        pubkey_packet = packet(tag=6, blob=self.pubkey_data)
        user_id_packet = packet(tag=13, blob=self.user_id)

        user_id_to_hash = user_id_packet[:1] + prefix_len('>L', self.user_id)
        data_to_sign = self.data_to_hash + user_id_to_hash
        log.info('signing user_id: %r', self.user_id.decode('ascii'))
        hashed_subpackets = [
            subpacket_time(self.created),  # signature creaion time
            subpacket_byte(0x1B, 1 | 2),  # key flags (certify & sign)
            subpacket_byte(0x15, 8),  # preferred hash (SHA256)
            subpacket_byte(0x16, 0),  # preferred compression (none)
            subpacket_byte(0x17, 0x80)]  # key server prefs (no-modify)
        signature = self._make_signature(visual='Sign GPG public key',
                                         data_to_sign=data_to_sign,
                                         sig_type=0x13,  # user id & public key
                                         hashed_subpackets=hashed_subpackets)

        sign_packet = packet(tag=2, blob=signature)
        return pubkey_packet + user_id_packet + sign_packet

    def sign(self, msg, sign_time=None):
        if sign_time is None:
            sign_time = int(time.time())

        log.info('signing message %r at %s', msg,
                 time_format(sign_time))
        hashed_subpackets = [subpacket_time(sign_time)]
        blob = self._make_signature(
            visual='Sign GPG message',
            data_to_sign=msg, hashed_subpackets=hashed_subpackets)
        return packet(tag=2, blob=blob)

    def _make_signature(self, visual, data_to_sign,
                        hashed_subpackets, sig_type=0):
        header = struct.pack('>BBBB',
                             4,         # version
                             sig_type,  # rfc4880 (section-5.2.1)
                             19,        # pubkey_alg (ECDSA)
                             8)         # hash_alg (SHA256)
        hashed = subpackets(*hashed_subpackets)
        unhashed = subpackets(
            subpacket(16, self.key_id)  # issuer key id
        )
        tail = b'\x04\xff' + struct.pack('>L', len(header) + len(hashed))
        data_to_hash = data_to_sign + header + hashed + tail

        log.debug('hashing %d bytes', len(data_to_hash))
        digest = hashlib.sha256(data_to_hash).digest()

        result = self.client_wrapper.connection.sign_identity(
            identity=self.identity,
            challenge_hidden=hashlib.sha256(data_to_hash).digest(),
            challenge_visual=visual,
            ecdsa_curve_name=self.ecdsa_curve_name)
        assert result.signature[:1] == b'\x00'
        sig = result.signature[1:]
        sig = [trezor_agent.util.bytes2num(sig[:32]),
               trezor_agent.util.bytes2num(sig[32:])]

        hash_prefix = digest[:2]  # used for decoder's sanity check
        signature = mpi(sig[0]) + mpi(sig[1])  # actual ECDSA signature
        return header + hashed + unhashed + hash_prefix + signature


def main():
    p = argparse.ArgumentParser()
    p.add_argument('user_id')
    p.add_argument('-t', '--time', type=int, default=int(time.time()))
    p.add_argument('-f', '--filename')
    p.add_argument('-a', '--armor', action='store_true', default=False)
    p.add_argument('-p', '--public-key', action='store_true', default=False)
    p.add_argument('-v', '--verbose', action='store_true', default=False)

    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')
    s = Signer(user_id=args.user_id.encode('ascii'), created=args.time)
    if args.public_key:
        open(args.user_id + '.pub', 'wb').write(s.export())
    if args.filename:
        data = open(args.filename, 'rb').read()
        sig, ext = s.sign(data), '.sig'
        if args.armor:
            sig, ext = armor_sig(sig), '.asc'
        open(args.filename + ext, 'wb').write(sig)
    s.close()


if __name__ == '__main__':
    main()
