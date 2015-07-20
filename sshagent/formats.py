import io
import hashlib
import base64
import ecdsa

from . import util

import logging
log = logging.getLogger(__name__)

DER_OCTET_STRING = b'\x04'
ECDSA_KEY_TYPE = 'ecdsa-sha2-nistp256'
ECDSA_CURVE_NAME = 'nistp256'

curve = ecdsa.NIST256p
hashfunc = hashlib.sha256


def fingerprint(blob):
    digest = hashlib.md5(blob).digest()
    return ':'.join('{:02x}'.format(c) for c in bytearray(digest))


def parse_pubkey(blob):
    s = io.BytesIO(blob)
    key_type = util.read_frame(s)
    log.debug('key type: %s', key_type)
    curve_name = util.read_frame(s)
    log.debug('curve name: %s', curve_name)
    point = util.read_frame(s)
    assert s.read() == b''
    _type, point = point[:1], point[1:]
    assert _type == DER_OCTET_STRING
    size = len(point) // 2
    assert len(point) == 2 * size
    coords = (util.bytes2num(point[:size]), util.bytes2num(point[size:]))
    log.debug('coordinates: %s', coords)
    fp = fingerprint(blob)

    point = ecdsa.ellipticcurve.Point(curve.curve, *coords)
    vk = ecdsa.VerifyingKey.from_public_point(point, curve, hashfunc)
    result = {
        'point': coords,
        'curve': curve_name,
        'fingerprint': fp,
        'type': key_type,
        'blob': blob,
        'size': size,
        'verifying_key': vk
    }
    return result


def parse_public_key(data):
    file_type, base64blob, name = data.split()
    blob = base64.b64decode(base64blob)
    result = parse_pubkey(blob)
    result['name'] = name.encode('ascii')
    assert result['type'] == file_type.encode('ascii')
    log.debug('loaded %s %s', file_type, result['fingerprint'])
    return result


def decompress_pubkey(pub):
    P = curve.curve.p()
    A = curve.curve.a()
    B = curve.curve.b()
    x = util.bytes2num(pub[1:33])
    beta = pow(int(x*x*x+A*x+B), int((P+1)//4), int(P))
    y = (P-beta) if ((beta + ord(pub[0])) % 2) else beta

    point = ecdsa.ellipticcurve.Point(curve.curve, x, y)
    vk = ecdsa.VerifyingKey.from_public_point(point, curve=curve,
                                              hashfunc=hashfunc)
    parts = [ECDSA_KEY_TYPE, ECDSA_CURVE_NAME, DER_OCTET_STRING + vk.to_string()]
    return ''.join([util.frame(p) for p in parts])


def export_public_key(pubkey, label):
    blob = decompress_pubkey(pubkey)
    log.debug('fingerprint: %s', fingerprint(blob))
    b64 = base64.b64encode(blob)
    return '{} {} {}\n'.format(ECDSA_KEY_TYPE, b64, label)
