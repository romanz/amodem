"""Device abstraction layer for GPG operations."""

from .. import factory, formats, util


class HardwareSigner(object):
    """Sign messages and get public keys from a hardware device."""

    def __init__(self, user_id, curve_name):
        """Connect to the device and retrieve required public key."""
        self.client_wrapper = factory.load()
        self.identity = self.client_wrapper.identity_type()
        self.identity.proto = 'gpg'
        self.identity.host = user_id
        self.curve_name = curve_name

    def pubkey(self, ecdh=False):
        """Return public key as VerifyingKey object."""
        addr = util.get_bip32_address(identity=self.identity, ecdh=ecdh)
        if ecdh:
            curve_name = formats.get_ecdh_curve_name(self.curve_name)
        else:
            curve_name = self.curve_name
        public_node = self.client_wrapper.connection.get_public_node(
            n=addr, ecdsa_curve_name=curve_name)

        return formats.decompress_pubkey(
            pubkey=public_node.node.public_key,
            curve_name=curve_name)

    def sign(self, digest):
        """Sign the digest and return a serialized signature."""
        result = self.client_wrapper.connection.sign_identity(
            identity=self.identity,
            challenge_hidden=digest,
            challenge_visual='',
            ecdsa_curve_name=self.curve_name)
        assert result.signature[:1] == b'\x00'
        sig = result.signature[1:]
        return (util.bytes2num(sig[:32]), util.bytes2num(sig[32:]))

    def ecdh(self, pubkey):
        """Derive shared secret using ECDH from remote public key."""
        result = self.client_wrapper.connection.get_ecdh_session_key(
            identity=self.identity,
            peer_public_key=pubkey,
            ecdsa_curve_name=formats.get_ecdh_curve_name(self.curve_name))
        assert len(result.session_key) in {65, 33}  # NIST256 or Curve25519
        assert result.session_key[:1] == b'\x04'
        return result.session_key

    def close(self):
        """Close the connection to the device."""
        self.client_wrapper.connection.close()
