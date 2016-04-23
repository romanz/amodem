#!/usr/bin/env python
import argparse
import base64
import binascii
import hashlib
import io
import logging
import struct
import subprocess
import time

from . import decode, check
from .. import client, factory, formats, util

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


def _dump_nist256(vk):
    return mpi((4 << 512) |
               (vk.pubkey.point.x() << 256) |
               (vk.pubkey.point.y()))


def _dump_ed25519(vk):
    return mpi((0x40 << 256) |
               util.bytes2num(vk.to_bytes()))


SUPPORTED_CURVES = {
    formats.CURVE_NIST256: {
        # https://tools.ietf.org/html/rfc6637#section-11
        'oid': b'\x2A\x86\x48\xCE\x3D\x03\x01\x07',
        'algo_id': 19,
        'dump': _dump_nist256
    },
    formats.CURVE_ED25519: {
        'oid': b'\x2B\x06\x01\x04\x01\xDA\x47\x0F\x01',
        'algo_id': 22,
        'dump': _dump_ed25519
    }
}


def find_curve_by_algo_id(algo_id):
    curve_name, = [name for name, info in SUPPORTED_CURVES.items()
                   if info['algo_id'] == algo_id]
    return curve_name


class Signer(object):

    def __init__(self, user_id, created, curve_name):
        self.user_id = user_id
        assert curve_name in formats.SUPPORTED_CURVES
        self.curve_name = curve_name
        self.client_wrapper = factory.load()

        self.identity = self.client_wrapper.identity_type()
        self.identity.proto = 'gpg'
        self.identity.host = user_id

        addr = client.get_address(self.identity)
        public_node = self.client_wrapper.connection.get_public_node(
            n=addr, ecdsa_curve_name=self.curve_name)

        self.verifying_key = formats.decompress_pubkey(
            pubkey=public_node.node.public_key,
            curve_name=self.curve_name)

        self.created = int(created)
        log.info('%s GPG public key %s created at %s', self.curve_name,
                 self.hex_short_key_id(), time_format(self.created))

    @classmethod
    def from_public_key(cls, pubkey, user_id):
        s = Signer(user_id=user_id,
                   created=pubkey['created'],
                   curve_name=find_curve_by_algo_id(pubkey['algo']))
        assert s.key_id() == pubkey['key_id']
        return s

    def _pubkey_data(self):
        curve_info = SUPPORTED_CURVES[self.curve_name]
        header = struct.pack('>BLB',
                             4,             # version
                             self.created,  # creation
                             curve_info['algo_id'])
        oid = prefix_len('>B', curve_info['oid'])
        blob = curve_info['dump'](self.verifying_key)
        return header + oid + blob

    def _pubkey_data_to_hash(self):
        return b'\x99' + prefix_len('>H', self._pubkey_data())

    def _fingerprint(self):
        return hashlib.sha1(self._pubkey_data_to_hash()).digest()

    def key_id(self):
        return self._fingerprint()[-8:]

    def hex_short_key_id(self):
        return hexlify(self.key_id()[-4:])

    def close(self):
        self.client_wrapper.connection.clear_session()
        self.client_wrapper.connection.close()

    def export(self):
        pubkey_packet = packet(tag=6, blob=self._pubkey_data())
        user_id_packet = packet(tag=13, blob=self.user_id)

        user_id_to_hash = user_id_packet[:1] + prefix_len('>L', self.user_id)
        data_to_sign = self._pubkey_data_to_hash() + user_id_to_hash
        log.info('signing public key "%s"', self.user_id)
        hashed_subpackets = [
            subpacket_time(self.created),  # signature creaion time
            subpacket_byte(0x1B, 1 | 2),  # key flags (certify & sign)
            subpacket_byte(0x15, 8),  # preferred hash (SHA256)
            subpacket_byte(0x16, 0),  # preferred compression (none)
            subpacket_byte(0x17, 0x80)]  # key server prefs (no-modify)
        signature = self._make_signature(visual=self.hex_short_key_id(),
                                         data_to_sign=data_to_sign,
                                         sig_type=0x13,  # user id & public key
                                         hashed_subpackets=hashed_subpackets)

        sign_packet = packet(tag=2, blob=signature)
        return pubkey_packet + user_id_packet + sign_packet

    def sign(self, msg, sign_time=None):
        if sign_time is None:
            sign_time = int(time.time())

        log.info('signing %d byte message at %s',
                 len(msg), time_format(sign_time))
        hashed_subpackets = [subpacket_time(sign_time)]
        blob = self._make_signature(
            visual=self.hex_short_key_id(),
            data_to_sign=msg, hashed_subpackets=hashed_subpackets)
        return packet(tag=2, blob=blob)

    def _make_signature(self, visual, data_to_sign,
                        hashed_subpackets, sig_type=0):
        curve_info = SUPPORTED_CURVES[self.curve_name]
        header = struct.pack('>BBBB',
                             4,         # version
                             sig_type,  # rfc4880 (section-5.2.1)
                             curve_info['algo_id'],
                             8)         # hash_alg (SHA256)
        hashed = subpackets(*hashed_subpackets)
        unhashed = subpackets(
            subpacket(16, self.key_id())  # issuer key id
        )
        tail = b'\x04\xff' + struct.pack('>L', len(header) + len(hashed))
        data_to_hash = data_to_sign + header + hashed + tail

        log.debug('hashing %d bytes', len(data_to_hash))
        digest = hashlib.sha256(data_to_hash).digest()

        result = self.client_wrapper.connection.sign_identity(
            identity=self.identity,
            challenge_hidden=digest,
            challenge_visual=visual,
            ecdsa_curve_name=self.curve_name)
        assert result.signature[:1] == b'\x00'
        sig = result.signature[1:]
        sig = [util.bytes2num(sig[:32]),
               util.bytes2num(sig[32:])]

        hash_prefix = digest[:2]  # used for decoder's sanity check
        signature = mpi(sig[0]) + mpi(sig[1])  # actual ECDSA signature
        return header + hashed + unhashed + hash_prefix + signature


def split_lines(body, size):
    lines = []
    for i in range(0, len(body), size):
        lines.append(body[i:i+size] + '\n')
    return ''.join(lines)


def armor(blob, type_str):
    head = '-----BEGIN PGP {}-----\nVersion: GnuPG v2\n\n'.format(type_str)
    body = base64.b64encode(blob)
    checksum = base64.b64encode(util.crc24(blob))
    tail = '-----END PGP {}-----\n'.format(type_str)
    return head + split_lines(body, 64) + '=' + checksum + '\n' + tail


def load_from_gpg(user_id):
    log.info('loading public key %r from local GPG keyring', user_id)
    pubkey_bytes = subprocess.check_output(['gpg2', '--export', user_id])
    return decode.load_public_key(io.BytesIO(pubkey_bytes))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('user_id')
    p.add_argument('filename', nargs='?')
    p.add_argument('-t', '--time', type=int, default=int(time.time()))
    p.add_argument('-a', '--armor', action='store_true', default=False)
    p.add_argument('-v', '--verbose', action='store_true', default=False)
    p.add_argument('-e', '--ecdsa-curve', default='nist256p1')

    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')
    user_id = args.user_id.encode('ascii')
    if not args.filename:
        s = Signer(user_id=user_id, created=args.time,
                   curve_name=args.ecdsa_curve)
        pubkey = s.export()
        ext = '.pub'
        if args.armor:
            pubkey = armor(pubkey, 'PUBLIC KEY BLOCK')
            ext = '.asc'
        filename = s.hex_short_key_id() + ext
        open(filename, 'wb').write(pubkey)
        log.info('import to local keyring using "gpg2 --import %s"', filename)
    else:
        pubkey = load_from_gpg(user_id)
        s = Signer.from_public_key(pubkey=pubkey, user_id=user_id)
        data = open(args.filename, 'rb').read()
        sig, ext = s.sign(data), '.sig'
        if args.armor:
            sig = armor(sig, 'SIGNATURE')
            ext = '.asc'
        filename = args.filename + ext
        open(filename, 'wb').write(sig)
        check.verify(pubkey=pubkey, sig_file=filename)

    s.close()


if __name__ == '__main__':
    main()
