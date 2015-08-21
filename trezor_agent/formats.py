import io
import hashlib
import base64
import ecdsa

from . import util

import logging
log = logging.getLogger(__name__)

DER_OCTET_STRING = b'\x04'
ECDSA_KEY_PREFIX = b'ecdsa-sha2-'
ECDSA_CURVE_NAME = b'nistp256'

hashfunc = hashlib.sha256


def fingerprint(blob):
    digest = hashlib.md5(blob).digest()
    return ':'.join('{:02x}'.format(c) for c in bytearray(digest))


def parse_pubkey(blob, curve=ecdsa.NIST256p):
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


def decompress_pubkey(pub, curve=ecdsa.NIST256p):
    P = curve.curve.p()
    A = curve.curve.a()
    B = curve.curve.b()
    x = util.bytes2num(pub[1:33])
    beta = pow(int(x*x*x+A*x+B), int((P+1)//4), int(P))

    p0 = util.bytes2num(pub[:1])
    y = (P-beta) if ((beta + p0) % 2) else beta

    point = ecdsa.ellipticcurve.Point(curve.curve, x, y)
    return ecdsa.VerifyingKey.from_public_point(point, curve=curve,
                                                hashfunc=hashfunc)


def serialize_verifying_key(vk):
    key_type = ECDSA_KEY_PREFIX + ECDSA_CURVE_NAME
    curve_name = ECDSA_CURVE_NAME
    key_blob = DER_OCTET_STRING + vk.to_string()
    parts = [key_type, curve_name, key_blob]
    return b''.join([util.frame(p) for p in parts])


def export_public_key(pubkey, label):
    blob = serialize_verifying_key(decompress_pubkey(pubkey))
    log.debug('fingerprint: %s', fingerprint(blob))
    b64 = base64.b64encode(blob).decode('ascii')
    key_type = ECDSA_KEY_PREFIX + ECDSA_CURVE_NAME
    return '{} {} {}\n'.format(key_type.decode('ascii'), b64, label)


def import_public_key(line):
    ''' Parse public key textual format, as saved at .pub file '''
    file_type, base64blob, name = line.split()
    blob = base64.b64decode(base64blob)
    result = parse_pubkey(blob)
    result['name'] = name.encode('ascii')
    assert result['type'] == file_type.encode('ascii')
    log.debug('loaded %s %s', file_type, result['fingerprint'])
    return result
