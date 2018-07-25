"""Device abstraction layer for GPG operations."""

import logging

from .. import formats, util
from ..device import interface

log = logging.getLogger(__name__)


def create_identity(user_id, curve_name):
    """Create GPG identity for hardware device."""
    result = interface.Identity(identity_str='gpg://', curve_name=curve_name)
    result.identity_dict['host'] = user_id
    return result


class Client:
    """Sign messages and get public keys from a hardware device."""

    def __init__(self, device):
        """C-tor."""
        self.device = device

    def pubkey(self, identity, ecdh=False):
        """Return public key as VerifyingKey object."""
        with self.device:
            pubkey = self.device.pubkey(ecdh=ecdh, identity=identity)
        return formats.decompress_pubkey(
            pubkey=pubkey, curve_name=identity.curve_name)

    def sign(self, identity, digest):
        """Sign the digest and return a serialized signature."""
        log.info('please confirm GPG signature on %s for "%s"...',
                 self.device, identity.to_string())
        if identity.curve_name == formats.CURVE_NIST256:
            digest = digest[:32]  # sign the first 256 bits
        log.debug('signing digest: %s', util.hexlify(digest))
        with self.device:
            sig = self.device.sign(blob=digest, identity=identity)
        return (util.bytes2num(sig[:32]), util.bytes2num(sig[32:]))

    def ecdh(self, identity, pubkey):
        """Derive shared secret using ECDH from remote public key."""
        log.info('please confirm GPG decryption on %s for "%s"...',
                 self.device, identity.to_string())
        with self.device:
            return self.device.ecdh(pubkey=pubkey, identity=identity)
