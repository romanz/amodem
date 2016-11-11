import ecdsa
import ed25519
import pytest

from .. import protocol
from ... import formats


def test_packet():
    assert protocol.packet(1, b'') == b'\x84\x00'
    assert protocol.packet(2, b'A') == b'\x88\x01A'
    blob = b'B' * 0xAB
    assert protocol.packet(3, blob) == b'\x8c\xAB' + blob
    blob = b'C' * 0x1234
    assert protocol.packet(3, blob) == b'\x8d\x12\x34' + blob
    blob = b'D' * 0x12345678
    assert protocol.packet(4, blob) == b'\x92\x12\x34\x56\x78' + blob


def test_subpackets():
    assert protocol.subpacket(1, b'') == b'\x01'
    assert protocol.subpacket(2, '>H', 0x0304) == b'\x02\x03\x04'
    assert protocol.subpacket_long(9, 0x12345678) == b'\x09\x12\x34\x56\x78'
    assert protocol.subpacket_time(0x12345678) == b'\x02\x12\x34\x56\x78'
    assert protocol.subpacket_byte(0xAB, 0xCD) == b'\xAB\xCD'
    assert protocol.subpackets() == b'\x00\x00'
    assert protocol.subpackets(b'ABC', b'12345') == b'\x00\x0A\x03ABC\x0512345'


def test_mpi():
    assert protocol.mpi(0x123) == b'\x00\x09\x01\x23'


def test_armor():
    data = bytearray(range(256))
    assert protocol.armor(data, 'TEST') == '''-----BEGIN PGP TEST-----
Version: GnuPG v2

AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4v
MDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5f
YGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6P
kJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/
wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v
8PHy8/T19vf4+fr7/P3+/w==
=W700
-----END PGP TEST-----
'''


def test_make_signature():
    def signer_func(digest):
        assert digest == (b'\xd0\xe5]|\x8bP\xe6\x91\xb3\xe8+\xf4A\xf0`(\xb1'
                          b'\xc7\xf4;\x86\x97s\xdb\x9a\xda\xee< \xcb\x9e\x00')
        return (7, 8)

    sig = protocol.make_signature(
        signer_func=signer_func,
        data_to_sign=b'Hello World!',
        public_algo=22,
        hashed_subpackets=[protocol.subpacket_time(1)],
        unhashed_subpackets=[],
        sig_type=25)
    assert sig == (b'\x04\x19\x16\x08\x00\x06\x05\x02'
                   b'\x00\x00\x00\x01\x00\x00\xd0\xe5\x00\x03\x07\x00\x04\x08')


def test_nist256p1():
    sk = ecdsa.SigningKey.from_secret_exponent(secexp=1, curve=ecdsa.NIST256p)
    vk = sk.get_verifying_key()
    pk = protocol.PublicKey(curve_name=formats.CURVE_NIST256,
                            created=42, verifying_key=vk)
    assert repr(pk) == 'GPG public key nist256p1/F82361D9'
    assert pk.keygrip() == b'\x95\x85.\x91\x7f\xe2\xc3\x91R\xba\x99\x81\x92\xb5y\x1d\xb1\\\xdc\xf0'


def test_nist256p1_ecdh():
    sk = ecdsa.SigningKey.from_secret_exponent(secexp=1, curve=ecdsa.NIST256p)
    vk = sk.get_verifying_key()
    pk = protocol.PublicKey(curve_name=formats.CURVE_NIST256,
                            created=42, verifying_key=vk, ecdh=True)
    assert repr(pk) == 'GPG public key nist256p1/5811DF46'
    assert pk.keygrip() == b'\x95\x85.\x91\x7f\xe2\xc3\x91R\xba\x99\x81\x92\xb5y\x1d\xb1\\\xdc\xf0'


def test_ed25519():
    sk = ed25519.SigningKey(b'\x00' * 32)
    vk = sk.get_verifying_key()
    pk = protocol.PublicKey(curve_name=formats.CURVE_ED25519,
                            created=42, verifying_key=vk)
    assert repr(pk) == 'GPG public key ed25519/36B40FE6'
    assert pk.keygrip() == b'\xbf\x01\x90l\x17\xb64\xa3-\xf4\xc0gr\x99\x18<\xddBQ?'


def test_curve25519():
    sk = ed25519.SigningKey(b'\x00' * 32)
    vk = sk.get_verifying_key()
    pk = protocol.PublicKey(curve_name=formats.ECDH_CURVE25519,
                            created=42, verifying_key=vk)
    assert repr(pk) == 'GPG public key curve25519/69460384'
    assert pk.keygrip() == b'x\xd6\x86\xe4\xa6\xfc;\x0fY\xe1}Lw\xc4\x9ed\xf1Q\x8a\x00'


def test_get_curve_name_by_oid():
    for name, info in protocol.SUPPORTED_CURVES.items():
        assert protocol.get_curve_name_by_oid(info['oid']) == name
    with pytest.raises(KeyError):
        protocol.get_curve_name_by_oid('BAD_OID')
