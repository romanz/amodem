import binascii

import pytest

from .. import formats


def test_fingerprint():
    fp = '5d:41:40:2a:bc:4b:2a:76:b9:71:9d:91:10:17:c5:92'
    assert formats.fingerprint(b'hello') == fp


_point = (
    44423495295951059636974944244307637263954375053872017334547086177777411863925,  # nopep8
    111713194882028655451852320740440245619792555065469028846314891587105736340201  # nopep8
)

_public_key = (
    'ecdsa-sha2-nistp256 '
    'AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTY'
    'AAABBBGI2zqveJSB+geQEWG46OvGs2h3+0qu7tIdsH8Wylr'
    'V19vttd7GR5rKvTWJt8b9ErthmnFALelAFKOB/u50jsuk= '
    'home\n'
)

_public_key_cert = (
    'ecdsa-sha2-nistp256-cert-v01@openssh.com '
    'AAAAKGVjZHNhLXNoYTItbmlzdHAyNTYtY2VydC12MDFAb3B'
    'lbnNzaC5jb20AAAAgohlAP8H3LPYWz3+w/E+RGDxG6tNAEE'
    '3Ao9Z6Pc66khEAAAAIbmlzdHAyNTYAAABBBGI2zqveJSB+g'
    'eQEWG46OvGs2h3+0qu7tIdsH8WylrV19vttd7GR5rKvTWJt'
    '8b9ErthmnFALelAFKOB/u50jsukAAAAAAAAAFQAAAAEAAAA'
    'IdW5pdFRlc3QAAAAIAAAABHVzZXIAAAAAAAAAAP////////'
    '//AAAAAAAAAIIAAAAVcGVybWl0LVgxMS1mb3J3YXJkaW5nA'
    'AAAAAAAABdwZXJtaXQtYWdlbnQtZm9yd2FyZGluZwAAAAAA'
    'AAAWcGVybWl0LXBvcnQtZm9yd2FyZGluZwAAAAAAAAAKcGV'
    'ybWl0LXB0eQAAAAAAAAAOcGVybWl0LXVzZXItcmMAAAAAAA'
    'AAAAAAADMAAAALc3NoLWVkMjU1MTkAAAAgf9gyPrF24CLZc'
    '0rHoZuI1+yjBFWt66G8oUmm20yRO8IAAABTAAAAC3NzaC1l'
    'ZDI1NTE5AAAAQCEgVgsR7fSgcTxuAWqMW4h42y7pt1BAKR4'
    'HTRg178tl7Vx8WoRtQcNirX9eggBcTA+5ILWmeY3uDN+soW'
    't7fwk= '
    'home\n'
)

_public_key_ed25519_cert = (
    'ssh-ed25519-cert-v01@openssh.com '
    'AAAAIHNzaC1lZDI1NTE5LWNlcnQtdjAxQG9wZW5zc2guY29'
    'tAAAAIK5TMdCnuxxy4rr0CTHLekAsnL4DAhFyksK5romkuw'
    'xgAAAAIFBdF2tjfSO8nLIi736is+f0erq28RTc7CkM11NZt'
    'TKRAAAAAAAAAAAAAAABAAAACXVuaXQtdGVzdAAAAA0AAAAJ'
    'dW5pdC10ZXN0AAAAAAAAAAD//////////wAAAAAAAACCAAA'
    'AFXBlcm1pdC1YMTEtZm9yd2FyZGluZwAAAAAAAAAXcGVybW'
    'l0LWFnZW50LWZvcndhcmRpbmcAAAAAAAAAFnBlcm1pdC1wb'
    '3J0LWZvcndhcmRpbmcAAAAAAAAACnBlcm1pdC1wdHkAAAAA'
    'AAAADnBlcm1pdC11c2VyLXJjAAAAAAAAAAAAAABoAAAAE2V'
    'jZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBC'
    'HF5pUcZLVlTUBzos8ojyN34KrS7TnGAZINhRsCoNuRV4NFN'
    'IlEYpEvSwlumQuDx6B1y4Va+3pYzBbZInm6vwgAAABjAAAA'
    'E2VjZHNhLXNoYTItbmlzdHAyNTYAAABIAAAAICUMX1taTy6'
    'y+1Aa1m7kXHI/Qv7ZZIeNp7ndmCRLFCSuAAAAIBaX43k0Ye'
    'Bk8a5zp6FyFCBYVOtis/DUbGm07d7miPnE '
    'hello\n'
)

_public_key_ed25519_cert_BLOB = (
    b'\x00\x00\x00 ssh-ed25519-cert-v01@openssh.com'
    b'\x00\x00\x00 \xaeS1\xd0\xa7\xbb\x1cr\xe2\xba'
    b'\xf4\t1\xcbz@,\x9c\xbe\x03\x02\x11r\x92\xc2\xb9'
    b'\xae\x89\xa4\xbb\x0c`\x00\x00\x00 P]\x17kc}#'
    b'\xbc\x9c\xb2"\xef~\xa2\xb3\xe7\xf4z\xba\xb6\xf1'
    b'\x14\xdc\xec)\x0c\xd7SY\xb52\x91\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00'
    b'\x00\tunit-test\x00\x00\x00\r\x00\x00\x00\tun'
    b'it-test\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff'
    b'\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00'
    b'\x00\x00\x82\x00\x00\x00\x15permit-X11-forwar'
    b'ding\x00\x00\x00\x00\x00\x00\x00\x17permit-ag'
    b'ent-forwarding\x00\x00\x00\x00\x00\x00\x00\x16'
    b'permit-port-forwarding\x00\x00\x00\x00\x00\x00'
    b'\x00\npermit-pty\x00\x00\x00\x00\x00\x00\x00'
    b'\x0epermit-user-rc\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00h\x00\x00\x00\x13ecdsa-sha2-n'
    b'istp256\x00\x00\x00\x08nistp256\x00\x00\x00A'
    b'\x04!\xc5\xe6\x95\x1cd\xb5eM@s\xa2\xcf(\x8f#w'
    b'\xe0\xaa\xd2\xed9\xc6\x01\x92\r\x85\x1b\x02\xa0'
    b'\xdb\x91W\x83E4\x89Db\x91/K\tn\x99\x0b\x83\xc7'
    b'\xa0u\xcb\x85Z\xfbzX\xcc\x16\xd9"y\xba\xbf\x08'
    b'\x00\x00\x00c\x00\x00\x00\x13ecdsa-sha2-nistp'
    b'256\x00\x00\x00H\x00\x00\x00 %\x0c_[ZO.\xb2\xfb'
    b'P\x1a\xd6n\xe4\\r?B\xfe\xd9d\x87\x8d\xa7\xb9'
    b'\xdd\x98$K\x14$\xae\x00\x00\x00 \x16\x97\xe3y'
    b'4a\xe0d\xf1\xaes\xa7\xa1r\x14 XT\xebb\xb3\xf0'
    b'\xd4li\xb4\xed\xde\xe6\x88\xf9\xc4'
)


def test_parse_public_key():
    key = formats.import_public_key(_public_key)
    assert key['name'] == b'home'
    assert key['point'] == _point

    assert key['curve'] == 'nist256p1'
    assert key['fingerprint'] == '4b:19:bc:0f:c8:7e:dc:fa:1a:e3:c2:ff:6f:e0:80:a2'  # nopep8
    assert key['type'] == b'ecdsa-sha2-nistp256'


def test_parse_public_key_cert():
    key = formats.import_public_key(_public_key_cert)
    assert key['name'] == b'home'
    assert key['point'] == _point

    assert key['curve'] == 'nist256p1'
    assert key['fingerprint'] == 'ab:ab:5d:9f:f4:33:f4:d0:c3:68:65:3b:94:86:de:22'  # nopep8
    assert key['type'] == b'ecdsa-sha2-nistp256-cert-v01@openssh.com'


def test_decompress():
    blob = '036236ceabde25207e81e404586e3a3af1acda1dfed2abbbb4876c1fc5b296b575'
    vk = formats.decompress_pubkey(binascii.unhexlify(blob),
                                   curve_name=formats.CURVE_NIST256)
    assert formats.export_public_key(vk, label='home') == _public_key


def test_parse_ed25519():
    pubkey = ('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFBdF2tj'
              'fSO8nLIi736is+f0erq28RTc7CkM11NZtTKR hello\n')
    p = formats.import_public_key(pubkey)
    assert p['name'] == b'hello'
    assert p['curve'] == 'ed25519'

    BLOB = (b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00 P]\x17kc}#'
            b'\xbc\x9c\xb2"\xef~\xa2\xb3\xe7\xf4z\xba\xb6\xf1\x14'
            b'\xdc\xec)\x0c\xd7SY\xb52\x91')
    assert p['blob'] == BLOB
    assert p['fingerprint'] == '6b:b0:77:af:e5:3a:21:6d:17:82:9b:06:19:03:a1:97'  # nopep8
    assert p['type'] == b'ssh-ed25519'


def test_parse_ed25519_cert():
    p = formats.import_public_key(_public_key_ed25519_cert)
    assert p['name'] == b'hello'
    assert p['curve'] == 'ed25519'

    assert p['blob'] == _public_key_ed25519_cert_BLOB
    assert p['fingerprint'] == '86:b6:17:3e:e1:5c:ba:e0:dc:86:80:b2:47:b4:ad:50'  # nopep8
    assert p['type'] == b'ssh-ed25519-cert-v01@openssh.com'


def test_export_ed25519():
    pub = (b'\x00P]\x17kc}#\xbc\x9c\xb2"\xef~\xa2\xb3\xe7\xf4'
           b'z\xba\xb6\xf1\x14\xdc\xec)\x0c\xd7SY\xb52\x91')
    vk = formats.decompress_pubkey(pub, formats.CURVE_ED25519)
    result = formats.serialize_verifying_key(vk)
    assert result == (b'ssh-ed25519',
                      b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00 P]\x17kc}#\xbc'
                      b'\x9c\xb2"\xef~\xa2\xb3\xe7\xf4z\xba\xb6\xf1\x14\xdc'
                      b'\xec)\x0c\xd7SY\xb52\x91')


def test_decompress_error():
    with pytest.raises(ValueError):
        formats.decompress_pubkey('', formats.CURVE_NIST256)


def test_curve_mismatch():
    # NIST256 public key
    blob = '036236ceabde25207e81e404586e3a3af1acda1dfed2abbbb4876c1fc5b296b575'
    with pytest.raises(ValueError):
        formats.decompress_pubkey(binascii.unhexlify(blob),
                                  curve_name=formats.CURVE_ED25519)

    blob = '00' * 33  # Dummy public key
    with pytest.raises(ValueError):
        formats.decompress_pubkey(binascii.unhexlify(blob),
                                  curve_name=formats.CURVE_NIST256)

    blob = 'FF' * 33  # Unsupported prefix byte
    with pytest.raises(ValueError):
        formats.decompress_pubkey(binascii.unhexlify(blob),
                                  curve_name=formats.CURVE_NIST256)


def test_serialize_error():
    with pytest.raises(TypeError):
        formats.serialize_verifying_key(None)


def test_get_ecdh_curve_name():
    for c in [formats.CURVE_NIST256, formats.ECDH_CURVE25519]:
        assert c == formats.get_ecdh_curve_name(c)

    assert (formats.ECDH_CURVE25519 ==
            formats.get_ecdh_curve_name(formats.CURVE_ED25519))
