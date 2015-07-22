import io
import re
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
            msg = '{:d} Trezor devices found'.format(len(devices))
            raise IOError(msg)
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
        self.client.close()

    def get_identity(self, label):
        return self.factory.parse_identity(label)

    def get_public_key(self, identity):
        assert identity.proto == 'ssh'
        label = _identity_to_string(identity)
        log.info('getting "%s" public key from Trezor...', label)
        addr = _get_address(identity)
        node = self.client.get_public_node(addr, self.curve_name)

        pubkey = node.node.public_key
        return formats.export_public_key(pubkey=pubkey, label=label)

    def sign_ssh_challenge(self, identity, blob):
        assert identity.proto == 'ssh'
        label = _identity_to_string(identity)
        msg = _parse_ssh_blob(blob)

        log.info('please confirm user %s connection to "%s" using Trezor...',
                 msg['user'], label)

        visual = identity.path  # not signed when proto='ssh'
        result = self.client.sign_identity(identity=identity,
                                           challenge_hidden=blob,
                                           challenge_visual=visual,
                                           ecdsa_curve_name=self.curve_name)
        public_key_blob = formats.decompress_pubkey(result.public_key)
        assert public_key_blob == msg['public_key']['blob']
        assert len(result.signature) == 65
        assert result.signature[0] == b'\x00'

        sig = result.signature[1:]
        r = util.bytes2num(sig[:32])
        s = util.bytes2num(sig[32:])
        return (r, s)


_identity_regexp = re.compile(''.join([
    '^'
    r'(?:(?P<proto>.*)://)?',
    r'(?:(?P<user>.*)@)?',
    r'(?P<host>.*?)',
    r'(?::(?P<port>\w*))?',
    r'(?P<path>/.*)?',
    '$'
]))


def _string_to_identity(s):
    m = _identity_regexp.match(s)
    result = m.groupdict()
    if not result.get('proto'):
        result['proto'] = 'ssh'  # otherwise, Trezor will use SECP256K1 curve

    log.debug('parsed identity: %s', result)
    return {k: v for k, v in result.items() if v}


def _identity_to_string(identity):
    result = [identity.proto + '://']
    if identity.user:
        result.append(identity.user + '@')
    result.append(identity.host)
    if identity.port:
        result.append(':' + identity.port)
    if identity.path:
        result.append(identity.path)
    return ''.join(result)


def _get_address(identity):
    index = struct.pack('<L', identity.index)
    addr = index + _identity_to_string(identity)
    log.debug('address string: %r', addr)
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
        public_key = util.read_frame(i)
        res['public_key'] = formats.parse_pubkey(public_key)
        assert not i.read()
        log.debug('%s: user %r via %r (%r)',
                  res['conn'], res['user'], res['auth'], res['key_type'])
        log.debug('nonce: %s', binascii.hexlify(res['nonce']))
        log.debug('fingerprint: %s', res['public_key']['fingerprint'])
    return res
