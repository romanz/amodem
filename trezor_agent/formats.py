"""SSH format parsing and formatting tools."""
import base64
import hashlib
import io
import logging

import ecdsa
import ed25519

from . import util

log = logging.getLogger(__name__)

# Supported ECDSA curves (for SSH and GPG)
CURVE_NIST256 = 'nist256p1'
CURVE_ED25519 = 'ed25519'
SUPPORTED_CURVES = {CURVE_NIST256, CURVE_ED25519}

# Supported ECDH curves (for GPG)
ECDH_NIST256 = 'nist256p1'
ECDH_CURVE25519 = 'curve25519'

# SSH key types
SSH_NIST256_DER_OCTET = b'\x04'
SSH_NIST256_KEY_PREFIX = b'ecdsa-sha2-'
SSH_NIST256_CURVE_NAME = b'nistp256'
SSH_NIST256_KEY_TYPE = SSH_NIST256_KEY_PREFIX + SSH_NIST256_CURVE_NAME
SSH_ED25519_KEY_TYPE = b'ssh-ed25519'
SUPPORTED_KEY_TYPES = {SSH_NIST256_KEY_TYPE, SSH_ED25519_KEY_TYPE}

hashfunc = hashlib.sha256


def fingerprint(blob):
    """
    Compute SSH fingerprint for specified blob.

    See https://en.wikipedia.org/wiki/Public_key_fingerprint for details.
    """
    digest = hashlib.md5(blob).digest()
    return ':'.join('{:02x}'.format(c) for c in bytearray(digest))


def parse_pubkey(blob):
    """
    Parse SSH public key from given blob.

    Construct a verifier for ECDSA signatures.
    The verifier returns the signatures in the required SSH format.
    Currently, NIST256P1 and ED25519 elliptic curves are supported.
    """
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

        def ecdsa_verifier(sig, msg):
            assert len(sig) == 2 * size
            sig_decode = ecdsa.util.sigdecode_string
            vk = ecdsa.VerifyingKey.from_public_point(point, curve, hashfunc)
            vk.verify(signature=sig, data=msg, sigdecode=sig_decode)
            parts = [sig[:size], sig[size:]]
            return b''.join([util.frame(b'\x00' + p) for p in parts])

        result.update(point=coords, curve=CURVE_NIST256,
                      verifier=ecdsa_verifier)

    if key_type == SSH_ED25519_KEY_TYPE:
        pubkey = util.read_frame(s)
        assert s.read() == b''

        def ed25519_verify(sig, msg):
            assert len(sig) == 64
            vk = ed25519.VerifyingKey(pubkey)
            vk.verify(sig, msg)
            return sig

        result.update(curve=CURVE_ED25519, verifier=ed25519_verify)

    return result


def _decompress_ed25519(pubkey):
    """Load public key from the serialized blob (stripping the prefix byte)."""
    if pubkey[:1] == b'\x00':
        # set by Trezor fsm_msgSignIdentity() and fsm_msgGetPublicKey()
        return ed25519.VerifyingKey(pubkey[1:])


def _decompress_nist256(pubkey):
    """
    Load public key from the serialized blob.

    The leading byte least-significant bit is used to decide how to recreate
    the y-coordinate from the specified x-coordinate. See bitcoin/main.py#L198
    (from https://github.com/vbuterin/pybitcointools/) for details.
    """
    if pubkey[:1] in {b'\x02', b'\x03'}:  # set by ecdsa_get_public_key33()
        curve = ecdsa.NIST256p
        P = curve.curve.p()
        A = curve.curve.a()
        B = curve.curve.b()
        x = util.bytes2num(pubkey[1:33])
        beta = pow(int(x * x * x + A * x + B), int((P + 1) // 4), int(P))

        p0 = util.bytes2num(pubkey[:1])
        y = (P - beta) if ((beta + p0) % 2) else beta

        point = ecdsa.ellipticcurve.Point(curve.curve, x, y)
        return ecdsa.VerifyingKey.from_public_point(point, curve=curve,
                                                    hashfunc=hashfunc)


def decompress_pubkey(pubkey, curve_name):
    """
    Load public key from the serialized blob.

    Raise ValueError on parsing error.
    """
    vk = None
    if len(pubkey) == 33:
        decompress = {
            CURVE_NIST256: _decompress_nist256,
            CURVE_ED25519: _decompress_ed25519,
            ECDH_CURVE25519: _decompress_ed25519,
        }[curve_name]
        vk = decompress(pubkey)

    if not vk:
        msg = 'invalid {!s} public key: {!r}'.format(curve_name, pubkey)
        raise ValueError(msg)

    return vk


def serialize_verifying_key(vk):
    """
    Serialize a public key into SSH format (for exporting to text format).

    Currently, NIST256P1 and ED25519 elliptic curves are supported.
    Raise TypeError on unsupported key format.
    """
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


def export_public_key(vk, label):
    """
    Export public key to text format.

    The resulting string can be written into a .pub file or
    appended to the ~/.ssh/authorized_keys file.
    """
    key_type, blob = serialize_verifying_key(vk)
    log.debug('fingerprint: %s', fingerprint(blob))
    b64 = base64.b64encode(blob).decode('ascii')
    return '{} {} {}\n'.format(key_type.decode('ascii'), b64, label)


def import_public_key(line):
    """Parse public key textual format, as saved at a .pub file."""
    log.debug('loading SSH public key: %r', line)
    file_type, base64blob, name = line.split()
    blob = base64.b64decode(base64blob)
    result = parse_pubkey(blob)
    result['name'] = name.encode('ascii')
    assert result['type'] == file_type.encode('ascii')
    log.debug('loaded %s public key: %s', file_type, result['fingerprint'])
    return result


def get_ecdh_curve_name(signature_curve_name):
    """Return appropriate curve for ECDH for specified signing curve."""
    return {
        CURVE_NIST256: ECDH_NIST256,
        CURVE_ED25519: ECDH_CURVE25519,
        ECDH_CURVE25519: ECDH_CURVE25519,
    }[signature_curve_name]
