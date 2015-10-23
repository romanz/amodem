import io
import hashlib
import base64
import ecdsa
import ed25519

from . import util

import logging
log = logging.getLogger(__name__)

# Supported ECDSA curves
CURVE_NIST256 = b'nist256p1'
CURVE_ED25519 = b'ed25519'
SUPPORTED_CURVES = {CURVE_NIST256, CURVE_ED25519}

# SSH key types
SSH_NIST256_DER_OCTET = b'\x04'
SSH_NIST256_KEY_PREFIX = b'ecdsa-sha2-'
SSH_NIST256_CURVE_NAME = b'nistp256'
SSH_NIST256_KEY_TYPE = SSH_NIST256_KEY_PREFIX + SSH_NIST256_CURVE_NAME
SSH_ED25519_KEY_TYPE = b'ssh-ed25519'
SUPPORTED_KEY_TYPES = {SSH_NIST256_KEY_TYPE, SSH_ED25519_KEY_TYPE}

hashfunc = hashlib.sha256


def fingerprint(blob):
    digest = hashlib.md5(blob).digest()
    return ':'.join('{:02x}'.format(c) for c in bytearray(digest))


def parse_pubkey(blob):
    fp = fingerprint(blob)
    s = io.BytesIO(blob)
    key_type = util.read_frame(s)
    log.debug('key type: %s', key_type)
    assert key_type in SUPPORTED_KEY_TYPES, key_type

    result = {'blob': blob, 'type': key_type, 'fingerprint': fp}

    if key_type == SSH_NIST256_KEY_TYPE:
        curve_name = util.read_frame(s)
        log.debug('curve name: %s', curve_name)
        point = util.read_frame(s)
        assert s.read() == b''
        _type, point = point[:1], point[1:]
        assert _type == SSH_NIST256_DER_OCTET
        size = len(point) // 2
        assert len(point) == 2 * size
        coords = (util.bytes2num(point[:size]), util.bytes2num(point[size:]))

        curve = ecdsa.NIST256p
        point = ecdsa.ellipticcurve.Point(curve.curve, *coords)
        vk = ecdsa.VerifyingKey.from_public_point(point, curve, hashfunc)

        def ecdsa_verifier(sig, msg):
            assert len(sig) == 2 * size
            sig_decode = ecdsa.util.sigdecode_string
            vk.verify(signature=sig, data=msg, sigdecode=sig_decode)
            parts = [sig[:size], sig[size:]]
            return b''.join([util.frame(b'\x00' + p) for p in parts])

        result.update(point=coords, curve=CURVE_NIST256,
                      verifier=ecdsa_verifier)

    if key_type == SSH_ED25519_KEY_TYPE:
        pubkey = util.read_frame(s)
        assert s.read() == b''
        vk = ed25519.VerifyingKey(pubkey)

        def ed25519_verify(sig, msg):
            assert len(sig) == 64
            vk.verify(sig, msg)
            return sig

        result.update(curve=CURVE_ED25519, verifier=ed25519_verify)

    return result


def decompress_pubkey(pub):
    if pub[:1] == b'\x00':
        # set by Trezor fsm_msgSignIdentity() and fsm_msgGetPublicKey()
        return ed25519.VerifyingKey(pub[1:])

    if pub[:1] in {b'\x02', b'\x03'}:  # set by ecdsa_get_public_key33()
        curve = ecdsa.NIST256p
        P = curve.curve.p()
        A = curve.curve.a()
        B = curve.curve.b()
        x = util.bytes2num(pub[1:33])
        beta = pow(int(x * x * x + A * x + B), int((P + 1) // 4), int(P))

        p0 = util.bytes2num(pub[:1])
        y = (P - beta) if ((beta + p0) % 2) else beta

        point = ecdsa.ellipticcurve.Point(curve.curve, x, y)
        return ecdsa.VerifyingKey.from_public_point(point, curve=curve,
                                                    hashfunc=hashfunc)
    raise ValueError('invalid {!r}', pub)


def serialize_verifying_key(vk):
    if isinstance(vk, ed25519.keys.VerifyingKey):
        pubkey = vk.to_bytes()
        key_type = SSH_ED25519_KEY_TYPE
        blob = util.frame(SSH_ED25519_KEY_TYPE) + util.frame(pubkey)
        return key_type, blob

    if isinstance(vk, ecdsa.keys.VerifyingKey):
        curve_name = SSH_NIST256_CURVE_NAME
        key_blob = SSH_NIST256_DER_OCTET + vk.to_string()
        parts = [SSH_NIST256_KEY_TYPE, curve_name, key_blob]
        key_type = SSH_NIST256_KEY_TYPE
        blob = b''.join([util.frame(p) for p in parts])
        return key_type, blob

    raise TypeError('unsupported {!r}'.format(vk))


def export_public_key(pubkey, label):
    assert len(pubkey) == 33
    key_type, blob = serialize_verifying_key(decompress_pubkey(pubkey))

    log.debug('fingerprint: %s', fingerprint(blob))
    b64 = base64.b64encode(blob).decode('ascii')
    return '{} {} {}\n'.format(key_type.decode('ascii'), b64, label)


def import_public_key(line):
    ''' Parse public key textual format, as saved at .pub file '''
    log.debug('loading SSH public key: %r', line)
    file_type, base64blob, name = line.split()
    blob = base64.b64decode(base64blob)
    result = parse_pubkey(blob)
    result['name'] = name.encode('ascii')
    assert result['type'] == file_type.encode('ascii')
    log.debug('loaded %s public key: %s', file_type, result['fingerprint'])
    return result
