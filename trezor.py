import io
import base64
import logging

from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport
from trezorlib.types_pb2 import IdentityType

import ecdsa
import bitcoin
import hashlib


import protocol
log = logging.getLogger(__name__)

curve = ecdsa.NIST256p
hashfunc = hashlib.sha256


def decode_pubkey(pub):
    P = curve.curve.p()
    A = curve.curve.a()
    B = curve.curve.b()
    x = bitcoin.decode(pub[1:33], 256)
    beta = pow(int(x*x*x+A*x+B), int((P+1)//4), int(P))
    y = (P-beta) if ((beta + bitcoin.from_byte_to_int(pub[0])) % 2) else beta
    return (x, y)


def export_public_key(pubkey, label):
    x, y = decode_pubkey(pubkey)
    point = ecdsa.ellipticcurve.Point(curve.curve, x, y)
    vk = ecdsa.VerifyingKey.from_public_point(point, curve=curve,
                                              hashfunc=hashfunc)
    key_type = 'ecdsa-sha2-nistp256'
    curve_name = 'nistp256'
    blobs = map(protocol.frame, [key_type, curve_name, '\x04' + vk.to_string()])
    b64 = base64.b64encode(''.join(blobs))
    return '{} {} {}\n'.format(key_type, b64, label)


def label_addr(ident):
    index = '\x00' * 4
    addr = index + '{}://{}'.format(ident.proto, ident.host)
    h = bytearray(hashfunc(addr).digest())

    address_n = [0] * 5
    address_n[0] = 13
    address_n[1] = h[0] | (h[1] << 8) | (h[2] << 16) | (h[3] << 24)
    address_n[2] = h[4] | (h[5] << 8) | (h[6] << 16) | (h[7] << 24)
    address_n[3] = h[8] | (h[9] << 8) | (h[10] << 16) | (h[11] << 24)
    address_n[4] = h[12] | (h[13] << 8) | (h[14] << 16) | (h[15] << 24)
    return [-x for x in address_n]  # prime each address component


class Client(object):

    proto = 'ssh'

    def __init__(self):
        device, = HidTransport.enumerate()
        client = TrezorClient(HidTransport(device))
        log.debug('connected to Trezor #%s', client.get_device_id())
        self.client = client

    def close(self):
        self.client.close()

    def _get_identity(self, label):
        return IdentityType(host=label, proto=self.proto)

    def get_public_key(self, label):
        addr = label_addr(self._get_identity(label))
        log.info('getting %r SSH public key from Trezor...', label)
        node = self.client.get_public_node(addr)
        return node.node.public_key

    def sign_ssh_challenge(self, label, blob):
        ident = self._get_identity(label)
        msg = parse_ssh_blob(blob)
        request = 'user: "{user}"'.format(**msg)

        log.info('confirm %s connection to %r using Trezor...',
                 request, label)
        s = self.client.sign_identity(identity=ident,
                                      challenge_hidden=blob,
                                      challenge_visual=request)
        r = protocol.bytes2num(s.signature[:32])
        s = protocol.bytes2num(s.signature[32:])
        return (r, s)


def parse_ssh_blob(data):
    res = {}
    if data:
        i = io.BytesIO(data)
        res['nonce'] = protocol.read_frame(i)
        i.read(1)  # TBD
        res['user'] = protocol.read_frame(i)
        res['conn'] = protocol.read_frame(i)
        res['auth'] = protocol.read_frame(i)
        i.read(1)  # TBD
        res['key_type'] = protocol.read_frame(i)
        res['pubkey'] = protocol.read_frame(i)
        log.debug('%s: user %r via %r (%r)',
                  res['conn'], res['user'], res['auth'], res['key_type'])
    return res
