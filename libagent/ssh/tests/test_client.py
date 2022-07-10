import io

import mock
import pytest

from .. import client, device, formats, util

ADDR = [2147483661, 2810943954, 3938368396, 3454558782, 3848009040]
CURVE = 'nist256p1'

PUBKEY = (b'\x03\xd8(\xb5\xa6`\xbet0\x95\xac:[;]\xdc,\xbd\xdc?\xd7\xc0\xec'
          b'\xdd\xbc+\xfar~\x9dAis')
PUBKEY_TEXT = ('ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzd'
               'HAyNTYAAABBBNgotaZgvnQwlaw6Wztd3Cy93D/XwOzdvCv6cn6dQWlzNMEQeW'
               'VUfhvrGljR2Z/CMRONY6ejB+9PnpUOPuzYqi8= <localhost:22|nist256p1>\n')


class MockDevice(device.interface.Device):  # pylint: disable=abstract-method

    @classmethod
    def package_name(cls):
        return 'fake-device-agent'

    def connect(self):
        return mock.Mock()

    def pubkey(self, identity, ecdh=False):  # pylint: disable=unused-argument
        assert self.conn
        return formats.decompress_pubkey(pubkey=PUBKEY, curve_name=identity.curve_name)

    def sign(self, identity, blob):
        """Sign given blob and return the signature (as bytes)."""
        assert self.conn
        assert blob == BLOB
        return SIG


BLOB = (b'\x00\x00\x00 \xce\xe0\xc9\xd5\xceu/\xe8\xc5\xf2\xbfR+x\xa1\xcf\xb0'
        b'\x8e;R\xd3)m\x96\x1b\xb4\xd8s\xf1\x99\x16\xaa2\x00\x00\x00\x05roman'
        b'\x00\x00\x00\x0essh-connection\x00\x00\x00\tpublickey'
        b'\x01\x00\x00\x00\x13ecdsa-sha2-nistp256\x00\x00\x00h\x00\x00\x00'
        b'\x13ecdsa-sha2-nistp256\x00\x00\x00\x08nistp256\x00\x00\x00A'
        b'\x04\xd8(\xb5\xa6`\xbet0\x95\xac:[;]\xdc,\xbd\xdc?\xd7\xc0\xec'
        b'\xdd\xbc+\xfar~\x9dAis4\xc1\x10yeT~\x1b\xeb\x1aX\xd1\xd9\x9f\xc21'
        b'\x13\x8dc\xa7\xa3\x07\xefO\x9e\x95\x0e>\xec\xd8\xaa/')

SIG = (b'R\x19T\xf2\x84$\xef#\x0e\xee\x04X\xc6\xc3\x99T`\xd1\xd8\xf7!'
       b'\x862@cx\xb8\xb9i@1\x1b3#\x938\x86]\x97*Y\xb2\x02Xa\xdf@\xecK'
       b'\xdc\xf0H\xab\xa8\xac\xa7? \x8f=C\x88N\xe2')


def test_ssh_agent():
    identity = device.interface.Identity(identity_str='localhost:22',
                                         curve_name=CURVE)
    c = client.Client(device=MockDevice())
    assert c.export_public_keys([identity]) == [PUBKEY_TEXT]
    signature = c.sign_ssh_challenge(blob=BLOB, identity=identity)

    key = formats.import_public_key(PUBKEY_TEXT)
    serialized_sig = key['verifier'](sig=signature, msg=BLOB)

    stream = io.BytesIO(serialized_sig)
    r = util.read_frame(stream)
    s = util.read_frame(stream)
    assert not stream.read()
    assert r[:1] == b'\x00'
    assert s[:1] == b'\x00'
    assert r[1:] + s[1:] == SIG

    # pylint: disable=unused-argument
    def cancel_sign(identity, blob):
        raise IOError(42, 'ERROR')

    c.device.sign = cancel_sign
    with pytest.raises(IOError):
        c.sign_ssh_challenge(blob=BLOB, identity=identity)


CHALLENGE_BLOB = (
    b'\x00\x00\x00 \xe4\x08\x8e"J#\x83 \x05\x90\x1e\xa9\xf9C\xb1\xd2\x8f\xc3\x8c\xea\xd8\xf6E'
    b'%q\xff\x07\xfa\xd8\x8b\xdf\xbd2\x00\x00\x00\x03git\x00\x00\x00\x0essh-connection\x00\x00'
    b'\x00\tpublickey\x01\x00\x00\x00\x0bssh-ed25519\x00\x00\x003\x00\x00\x00\x0bssh-ed25519'
    b'\x00\x00\x00 \xd1q\x1ab\xc6\xf0d\x19\xe2q<\x05\x0b\xdao\xa1\xcb\xae\xad\xc9\x0b\x16\xf3'
    b'\xc2m\x84q8qU\xda\xb0'
)


def test_parse_ssh_challenge():
    result = client.parse_ssh_blob(CHALLENGE_BLOB)
    result['public_key'].pop('verifier')
    assert result == {
        'auth': b'publickey',
        'conn': b'ssh-connection',
        'key_type': b'ssh-ed25519',
        'nonce': b'\xe4\x08\x8e"J#\x83 \x05\x90\x1e\xa9\xf9C\xb1\xd2\x8f\xc3\x8c\xea'
                 b'\xd8\xf6E%q\xff\x07\xfa\xd8\x8b\xdf\xbd',
        'public_key': {'blob': b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00 \xd1'
                               b'q\x1ab\xc6\xf0d\x19\xe2q<\x05\x0b\xdao\xa1\xcb'
                               b'\xae\xad\xc9\x0b\x16\xf3\xc2m\x84q8qU\xda\xb0',
                       'curve': 'ed25519',
                       'fingerprint': '47:a3:26:af:0b:5d:a2:c3:91:ed:26:36:94:be:3a:d5',
                       'type': b'ssh-ed25519'},
        'sshsig': False,
        'user': b'git',
    }


FILE_SIG_BLOB = (
    b"SSHSIG\x00\x00\x00\x04file\x00\x00\x00\x00\x00\x00\x00\x06sha512\x00\x00\x00@r\xb7r\xfeM"
    b"\xe5w\xf0#w\x1dbl\xca\to=\x90\xb69\xd1:u{\xe5\xe4\xf1\xb1\xa8C\xb8\xfcM\x91\x9f\x12\xa8"
    b"\x1d`\x00\x848C<\x85\x8e\xf0o\xdab\xdcQ\xce\xf2\xda\xc3\xae\xa9\x1e%\x85\xcd\xe3'"
)


def test_parse_ssh_signature():
    result = client.parse_ssh_blob(FILE_SIG_BLOB)
    assert result == {
        'hashalg': b'sha512',
        'message': b'r\xb7r\xfeM\xe5w\xf0#w\x1dbl\xca\to=\x90\xb69\xd1:u{'
                   b'\xe5\xe4\xf1\xb1\xa8C\xb8\xfcM\x91\x9f\x12\xa8\x1d`\x00\x848C<'
                   b"\x85\x8e\xf0o\xdab\xdcQ\xce\xf2\xda\xc3\xae\xa9\x1e%\x85\xcd\xe3'",
        'namespace': b'file',
        'reserved': b'',
        'sshsig': True,
    }
