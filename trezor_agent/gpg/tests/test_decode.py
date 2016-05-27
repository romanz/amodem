import io

from .. import decode
from ... import util


def test_subpackets():
    s = io.BytesIO(b'\x00\x05\x02\xAB\xCD\x01\xEF')
    assert decode.parse_subpackets(util.Reader(s)) == [b'\xAB\xCD', b'\xEF']


def test_mpi():
    s = io.BytesIO(b'\x00\x09\x01\x23')
    assert decode.parse_mpi(util.Reader(s)) == 0x123


def assert_subdict(d, s):
    for k, v in s.items():
        assert d[k] == v


def test_primary_nist256p1():
    # pylint: disable=line-too-long
    data = b'''-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v2

mFIEV0hI1hMIKoZIzj0DAQcCAwTXY7aq01xMPSU7gTHU9B7Z2CFoCk1Y4WYb8Tiy
hurvIZ5la6+UEgAKF9HXpQo0yE+HQOgufoLlCpdE7NoEUb+HtAd0ZXN0aW5niHYE
ExMIABIFAldISNYCGwMCFQgCFgACF4AAFgkQTcCehfpEIPILZFRSRVpPUi1HUEeV
3QEApHKmBkbLVZNpsB8q9mBzKytxnOHNB3QWDuoKJu/ERi4A/1wRGZ/B0BDazHck
zpR9luXTKwMEl+mlZmwEFKZXBmir
=oyj0
-----END PGP PUBLIC KEY BLOCK-----
'''
    stream = util.Reader(io.BytesIO(decode.remove_armor(data)))
    pubkey, user_id, signature = list(decode.parse_packets(stream))
    assert_subdict(pubkey, {
        'created': 1464355030, 'type': 'pubkey', 'tag': 6,
        'version': 4, 'algo': 19, 'key_id': b'M\xc0\x9e\x85\xfaD \xf2',
        '_to_hash': b'\x99\x00R\x04WHH\xd6\x13\x08*\x86H\xce=\x03\x01\x07\x02\x03\x04\xd7c\xb6\xaa\xd3\\L=%;\x811\xd4\xf4\x1e\xd9\xd8!h\nMX\xe1f\x1b\xf18\xb2\x86\xea\xef!\x9eek\xaf\x94\x12\x00\n\x17\xd1\xd7\xa5\n4\xc8O\x87@\xe8.~\x82\xe5\n\x97D\xec\xda\x04Q\xbf\x87'  # nopep8
    })
    point = pubkey['verifying_key'].pubkey.point
    assert point.x(), point.y() == (
        97423441028100245505102979561460969898742433559010922791700160771755342491425,
        71644624850142103522769833619875243486871666152651730678601507641225861250951
    )
    assert_subdict(user_id, {
        'tag': 13, 'type': 'user_id', 'value': b'testing',
        '_to_hash': b'\xb4\x00\x00\x00\x07testing'
    })
    assert_subdict(signature, {
        'pubkey_alg': 19, '_is_custom': True, 'hash_alg': 8, 'tag': 2,
        'sig_type': 19, 'version': 4, 'type': 'signature', 'hash_prefix': b'\x95\xdd',
        'sig': (74381873592149178031432444136130575481350858387410643140628758456112511206958,
                41642995320462795718437755373080464775445470754419831653624197847615308982443),
        'hashed_subpackets': [b'\x02WHH\xd6', b'\x1b\x03', b'\x15\x08', b'\x16\x00', b'\x17\x80'],
        'unhashed_subpackets': [b'\x10M\xc0\x9e\x85\xfaD \xf2', b'dTREZOR-GPG'],
        '_to_hash': b'\x04\x13\x13\x08\x00\x12\x05\x02WHH\xd6\x02\x1b\x03\x02\x15\x08\x02\x16\x00\x02\x17\x80\x04\xff\x00\x00\x00\x18'  # nopep8
    })
