import binascii

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


def test_parse_public_key():
    key = formats.import_public_key(_public_key)
    assert key['name'] == b'home'
    assert key['point'] == _point

    assert key['curve'] == b'nistp256'
    assert key['fingerprint'] == '4b:19:bc:0f:c8:7e:dc:fa:1a:e3:c2:ff:6f:e0:80:a2'  # nopep8
    assert key['type'] == b'ecdsa-sha2-nistp256'
    assert key['size'] == 32


def test_decompress():
    blob = '036236ceabde25207e81e404586e3a3af1acda1dfed2abbbb4876c1fc5b296b575'
    result = formats.export_public_key(binascii.unhexlify(blob), label='home')
    assert result == _public_key
