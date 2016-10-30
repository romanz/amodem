"""Device abstraction layer for GPG operations."""

import logging

from .. import device, formats, util

log = logging.getLogger(__name__)


class Client(object):
    """Sign messages and get public keys from a hardware device."""

    def __init__(self, user_id, curve_name):
        """Connect to the device and retrieve required public key."""
        self.device = device.detect(identity_str='',
                                    curve_name=curve_name)
        self.device.identity_dict['proto'] = 'gpg'
        self.device.identity_dict['host'] = user_id
        self.user_id = user_id

    def pubkey(self, ecdh=False):
        """Return public key as VerifyingKey object."""
        with self.device:
            pubkey = self.device.pubkey(ecdh=ecdh)
        return formats.decompress_pubkey(
            pubkey=pubkey, curve_name=self.device.curve_name)

    def sign(self, digest):
        """Sign the digest and return a serialized signature."""
        log.info('please confirm GPG signature on %s for "%s"...',
                 self.device, self.user_id)
        if self.device.curve_name == formats.CURVE_NIST256:
            digest = digest[:32]  # sign the first 256 bits
        log.debug('signing digest: %s', util.hexlify(digest))
        with self.device:
            sig = self.device.sign(blob=digest)
        return (util.bytes2num(sig[:32]), util.bytes2num(sig[32:]))

    def ecdh(self, pubkey):
        """Derive shared secret using ECDH from remote public key."""
        log.info('please confirm GPG decryption on %s for "%s"...',
                 self.device, self.user_id)
        with self.device:
            return self.device.ecdh(pubkey=pubkey)
