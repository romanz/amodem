import io
import binascii

from . import util
from . import formats

import logging
log = logging.getLogger(__name__)


class TrezorLibrary(object):

    @staticmethod
    def client():
        from trezorlib.client import TrezorClient
        from trezorlib.transport_hid import HidTransport
        devices = HidTransport.enumerate()
        if len(devices) != 1:
            raise ValueError('{:d} Trezor devices found'.format(len(devices)))
        return TrezorClient(HidTransport(devices[0]))

    @staticmethod
    def identity(label, proto='ssh'):
        from trezorlib.types_pb2 import IdentityType
        return IdentityType(host=label, proto=proto)


class Client(object):

    def __init__(self, factory=TrezorLibrary):
        self.factory = factory
        self.client = self.factory.client()
        f = self.client.features
        log.info('connected to Trezor')
        log.debug('ID       : %s', f.device_id)
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

    def get_public_key(self, label):
        addr = _get_address(self.factory.identity(label))
        log.info('getting %r SSH public key from Trezor...', label)
        node = self.client.get_public_node(addr)
        return node.node.public_key

    def sign_ssh_challenge(self, label, blob):
        ident = self.factory.identity(label)
        msg = _parse_ssh_blob(blob)
        request = 'user: "{user}"'.format(**msg)

        log.info('confirm %s connection to %r using Trezor...',
                 request, label)
        s = self.client.sign_identity(identity=ident,
                                      challenge_hidden=blob,
                                      challenge_visual=request)
        assert len(s.signature) == 64
        r = util.bytes2num(s.signature[:32])
        s = util.bytes2num(s.signature[32:])
        return (r, s)


def _get_address(ident):
    index = '\x00' * 4
    addr = index + '{}://{}'.format(ident.proto, ident.host)
    digest = formats.hashfunc(addr).digest()
    s = io.BytesIO(bytearray(digest))

    address_n = [13] + list(util.recv(s, '<LLLL'))
    return [-a for a in address_n]  # prime each address component


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
    return res
