"""Fake device - ONLY FOR TESTS!!! (NEVER USE WITH REAL DATA)."""

import hashlib
import logging

import ecdsa

from . import interface
from .. import formats

log = logging.getLogger(__name__)


def _verify_support(identity):
    """Make sure the device supports given configuration."""
    if identity.curve_name not in {formats.CURVE_NIST256}:
        raise NotImplementedError(
            'Unsupported elliptic curve: {}'.format(identity.curve_name))


class FakeDevice(interface.Device):
    """Connection to TREZOR device."""

    @classmethod
    def package_name(cls):
        """Python package name."""
        return 'fake-device-agent'

    def connect(self):
        """Return "dummy" connection."""
        log.critical('NEVER USE THIS CODE FOR REAL-LIFE USE-CASES!!!')
        log.critical('ONLY FOR DEBUGGING AND TESTING!!!')
        # The code below uses HARD-CODED secret key - and should be used ONLY
        # for GnuPG integration tests (e.g. when no real device is available).
        # pylint: disable=attribute-defined-outside-init
        self.secexp = 1
        self.sk = ecdsa.SigningKey.from_secret_exponent(
            secexp=self.secexp, curve=ecdsa.curves.NIST256p, hashfunc=hashlib.sha256)
        self.vk = self.sk.get_verifying_key()
        return self

    def close(self):
        """Close connection."""
        self.conn = None

    def pubkey(self, identity, ecdh=False):
        """Return public key."""
        _verify_support(identity)
        data = self.vk.to_string()
        x, y = data[:32], data[32:]
        prefix = bytearray([2 + (bytearray(y)[0] & 1)])
        return bytes(prefix) + x

    def sign(self, identity, blob):
        """Sign given blob and return the signature (as bytes)."""
        if identity.identity_dict['proto'] in {'ssh'}:
            digest = hashlib.sha256(blob).digest()
        else:
            digest = blob
        return self.sk.sign_digest_deterministic(digest=digest,
                                                 hashfunc=hashlib.sha256)

    def ecdh(self, identity, pubkey):
        """Get shared session key using Elliptic Curve Diffie-Hellman."""
        assert pubkey[:1] == b'\x04'
        peer = ecdsa.VerifyingKey.from_string(
            pubkey[1:],
            curve=ecdsa.curves.NIST256p,
            hashfunc=hashlib.sha256)
        shared = ecdsa.VerifyingKey.from_public_point(
            point=(peer.pubkey.point * self.secexp),
            curve=ecdsa.curves.NIST256p,
            hashfunc=hashlib.sha256)
        return shared.to_string()
