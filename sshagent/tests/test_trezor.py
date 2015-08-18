from ..trezor import client

import mock


ADDR = [2147483661, 2810943954, 3938368396, 3454558782, 3848009040]
CURVE = 'nist256p1'

PUBKEY = (b'\x03\xd8(\xb5\xa6`\xbet0\x95\xac:[;]\xdc,\xbd\xdc?\xd7\xc0\xec'
          b'\xdd\xbc+\xfar~\x9dAis')
PUBKEY_TEXT = ('ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzd'
               'HAyNTYAAABBBNgotaZgvnQwlaw6Wztd3Cy93D/XwOzdvCv6cn6dQWlzNMEQeW'
               'VUfhvrGljR2Z/CMRONY6ejB+9PnpUOPuzYqi8= ssh://localhost:22\n')


class ConnectionMock(object):

    def __init__(self):
        self.features = mock.Mock(spec=[])
        self.features.device_id = '123456789'
        self.features.label = 'mywallet'
        self.features.vendor = 'mock'
        self.features.major_version = 1
        self.features.minor_version = 2
        self.features.patch_version = 3
        self.features.revision = b'456'
        self.closed = False

    def close(self):
        self.closed = True

    def get_public_node(self, addr, ecdsa_curve_name):
        assert not self.closed
        assert addr == ADDR
        assert ecdsa_curve_name == CURVE
        result = mock.Mock(spec=[])
        result.node = mock.Mock(spec=[])
        result.node.public_key = PUBKEY
        return result


class FactoryMock(object):

    @staticmethod
    def client():
        return ConnectionMock()

    @staticmethod
    def identity_type(**kwargs):
        result = mock.Mock(spec=[])
        result.index = 0
        result.proto = result.user = result.host = result.port = None
        result.path = None
        for k, v in kwargs.items():
            setattr(result, k, v)
        return result


def test_client():
    c = client.Client(factory=FactoryMock)
    ident = c.get_identity(label='localhost:22', protocol='ssh')
    assert ident.host == 'localhost'
    assert ident.proto == 'ssh'
    assert ident.port == '22'
    assert ident.user is None
    assert ident.path is None

    with c:
        assert c.get_public_key(ident) == PUBKEY_TEXT
