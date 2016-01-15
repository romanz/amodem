import binascii
import io
import logging
import re
import struct

from . import factory
from .. import formats, util

log = logging.getLogger(__name__)


class Client(object):

    def __init__(self, loader=factory.load, curve=formats.CURVE_NIST256):
        client_wrapper = loader()
        self.client = client_wrapper.connection
        self.identity_type = client_wrapper.identity_type
        self.device_name = client_wrapper.device_name
        self.curve = curve

    def __enter__(self):
        msg = 'Hello World!'
        assert self.client.ping(msg) == msg
        return self

    def __exit__(self, *args):
        log.info('disconnected from %s', self.device_name)
        self.client.clear_session()  # forget PIN and shutdown screen
        self.client.close()

    def get_identity(self, label):
        identity = string_to_identity(label, self.identity_type)
        identity.proto = 'ssh'
        return identity

    def get_public_key(self, label):
        identity = self.get_identity(label=label)
        label = identity_to_string(identity)  # canonize key label
        log.info('getting "%s" public key (%s) from %s...',
                 label, self.curve, self.device_name)
        addr = _get_address(identity)
        node = self.client.get_public_node(n=addr,
                                           ecdsa_curve_name=self.curve)

        pubkey = node.node.public_key
        vk = formats.decompress_pubkey(pubkey=pubkey, curve_name=self.curve)
        return formats.export_public_key(vk=vk, label=label)

    def sign_ssh_challenge(self, label, blob):
        identity = self.get_identity(label=label)
        msg = _parse_ssh_blob(blob)

        log.info('please confirm user "%s" login to "%s" using %s...',
                 msg['user'], label, self.device_name)

        visual = identity.path  # not signed when proto='ssh'
        result = self.client.sign_identity(identity=identity,
                                           challenge_hidden=blob,
                                           challenge_visual=visual,
                                           ecdsa_curve_name=self.curve)

        verifying_key = formats.decompress_pubkey(pubkey=result.public_key,
                                                  curve_name=self.curve)
        key_type, blob = formats.serialize_verifying_key(verifying_key)
        assert blob == msg['public_key']['blob']
        assert key_type == msg['key_type']
        assert len(result.signature) == 65
        assert result.signature[:1] == bytearray([0])

        return result.signature[1:]


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
