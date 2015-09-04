import io
import re
import struct
import binascii

from .. import util
from .. import formats
from . import _factory as TrezorFactory

import logging
log = logging.getLogger(__name__)


class Client(object):

    MIN_VERSION = [1, 3, 4]

    def __init__(self, factory=TrezorFactory):
        self.factory = factory
        self.client = self.factory.client()
        f = self.client.features
        log.debug('connected to Trezor %s', f.device_id)
        log.debug('label    : %s', f.label)
        log.debug('vendor   : %s', f.vendor)
        version = [f.major_version, f.minor_version, f.patch_version]
        version_str = '.'.join([str(v) for v in version])
        log.debug('version  : %s', version_str)
        log.debug('revision : %s', binascii.hexlify(f.revision))
        if version < self.MIN_VERSION:
            fmt = 'Please upgrade your TREZOR to v{}+ firmware'
            version_str = '.'.join([str(v) for v in self.MIN_VERSION])
            raise ValueError(fmt.format(version_str))

    def __enter__(self):
        msg = 'Hello World!'
        assert self.client.ping(msg) == msg
        return self

    def __exit__(self, *args):
        log.info('disconnected from Trezor')
        self.client.clear_session()  # forget PIN and shutdown screen
        self.client.close()

    def get_identity(self, label):
        identity = string_to_identity(label, self.factory.identity_type)
        identity.proto = 'ssh'
        return identity

    def get_public_key(self, identity):
        assert identity.proto == 'ssh'
        label = identity_to_string(identity)
        log.info('getting "%s" public key from Trezor...', label)
        addr = _get_address(identity)
        node = self.client.get_public_node(n=addr,
                                           ecdsa_curve_name='nist256p1')

        pubkey = node.node.public_key
        return formats.export_public_key(pubkey=pubkey, label=label)

    def sign_ssh_challenge(self, identity, blob):
        assert identity.proto == 'ssh'
        label = identity_to_string(identity)
        msg = _parse_ssh_blob(blob)

        log.info('please confirm user "%s" login to "%s" using Trezor...',
                 msg['user'], label)

        visual = identity.path  # not signed when proto='ssh'
        result = self.client.sign_identity(identity=identity,
                                           challenge_hidden=blob,
                                           challenge_visual=visual,
                                           ecdsa_curve_name='nist256p1')
        verifying_key = formats.decompress_pubkey(result.public_key)
        public_key_blob = formats.serialize_verifying_key(verifying_key)
        assert public_key_blob == msg['public_key']['blob']
        assert len(result.signature) == 65
        assert result.signature[:1] == bytearray([0])

        return parse_signature(result.signature)


def parse_signature(blob):
    sig = blob[1:]
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


def string_to_identity(s, identity_type):
    m = _identity_regexp.match(s)
    result = m.groupdict()
    log.debug('parsed identity: %s', result)
    kwargs = {k: v for k, v in result.items() if v}
    return identity_type(**kwargs)


def identity_to_string(identity):
    result = []
    if identity.proto:
        result.append(identity.proto + '://')
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
    addr = index + identity_to_string(identity).encode('ascii')
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
