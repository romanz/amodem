import io
import struct
import binascii

from . import util
from . import formats

import logging
log = logging.getLogger(__name__)


class TrezorLibrary(object):

    @staticmethod
    def client():
        # pylint: disable=import-error
        from trezorlib.client import TrezorClient
        from trezorlib.transport_hid import HidTransport
        devices = HidTransport.enumerate()
        if len(devices) != 1:
            raise ValueError('{:d} Trezor devices found'.format(len(devices)))
        return TrezorClient(HidTransport(devices[0]))

    @staticmethod
    def parse_identity(s):
        # pylint: disable=import-error
        from trezorlib.types_pb2 import IdentityType
        return IdentityType(**_string_to_identity(s))


class Client(object):

    curve_name = 'nist256p1'

    def __init__(self, factory=TrezorLibrary):
        self.factory = factory
        self.client = self.factory.client()
        f = self.client.features
        log.debug('connected to Trezor %s', f.device_id)
        log.debug('label    : %s', f.label)
        log.debug('vendor   : %s', f.vendor)
        version = [f.major_version, f.minor_version, f.patch_version]
        log.debug('version  : %s', '.'.join([str(v) for v in version]))
        log.debug('revision : %s', binascii.hexlify(f.revision))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        log.info('disconnected from Trezor')
        self.client.clear_session()
        self.client.close()

    def get_identity(self, label):
        return self.factory.parse_identity(label)

    def get_public_key(self, identity):
        label = _identity_to_string(identity)
        log.info('getting "%s" public key from Trezor...', label)
        addr = _get_address(identity)
        node = self.client.get_public_node(addr, self.curve_name)

        pubkey = node.node.public_key
        return formats.export_public_key(pubkey=pubkey, label=label)

    def sign_ssh_challenge(self, label, blob):
        identity = self.factory.parse_identity(label)
        msg = _parse_ssh_blob(blob)

        log.info('confirm user %s connection to %r using Trezor...',
                 msg['user'], label)
        s = self.client.sign_identity(identity=identity,
                                      challenge_hidden=blob,
                                      challenge_visual='',
                                      ecdsa_curve_name=self.curve_name)
        assert len(s.signature) == 65
        assert s.signature[0] == b'\x00'

        sig = s.signature[1:]
        r = util.bytes2num(sig[:32])
        s = util.bytes2num(sig[32:])
        return (r, s)


def _lsplit(s, sep):
    p = None
    if sep in s:
        p, s = s.split(sep, 1)
    return (p, s)


def _rsplit(s, sep):
    p = None
    if sep in s:
        s, p = s.rsplit(sep, 1)
    return (s, p)


def _string_to_identity(s):
    proto, s = _lsplit(s, '://')
    user, s = _lsplit(s, '@')
    s, path = _rsplit(s, '/')
    host, port = _rsplit(s, ':')

    if not proto:
        proto = 'ssh'  # otherwise, Trezor will use SECP256K1 curve

    result = [
        ('proto', proto), ('user', user), ('host', host),
        ('port', port), ('path', path)
    ]
    return {k: v for k, v in result if v}


def _identity_to_string(identity):
    result = []
    if identity.proto:
        result.append(identity.proto + '://')
    if identity.user:
        result.append(identity.user + '@')
    result.append(identity.host)
    if identity.port:
        result.append(':' + identity.port)
    if identity.path:
        result.append('/' + identity.path)
    return ''.join(result)


def _get_address(identity):
    index = struct.pack('<L', identity.index)
    addr = index + _identity_to_string(identity)
    digest = formats.hashfunc(addr).digest()
    s = io.BytesIO(bytearray(digest))

    hardened = 0x80000000
    address_n = [13] + list(util.recv(s, '<LLLL'))
    return [(hardened | value) for value in address_n]


def _parse_ssh_blob(data):
    res = {}
    if data:
        i = io.BytesIO(data)
        res['nonce'] = util.read_frame(i)
        i.read(1)  # TBD
        res['user'] = util.read_frame(i)
        res['conn'] = util.read_frame(i)
        res['auth'] = util.read_frame(i)
        i.read(1)  # TBD
        res['key_type'] = util.read_frame(i)
        res['pubkey'] = util.read_frame(i)
        log.debug('%s: user %r via %r (%r)',
                  res['conn'], res['user'], res['auth'], res['key_type'])
        log.debug('nonce: %s', binascii.hexlify(res['nonce']))
        pubkey = formats.parse_pubkey(res['pubkey'])
        log.debug('fingerprint: %s', pubkey['fingerprint'])
    return res
