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

    def connect(self):  # pylint: disable=no-self-use
        return mock.Mock()

    def pubkey(self, identity, ecdh=False):  # pylint: disable=unused-argument
        assert self.conn
        return PUBKEY

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
