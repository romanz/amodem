"""KeepKey-related code (see https://www.keepkey.com/)."""

from .. import formats
from . import trezor


def _verify_support(identity, ecdh):
    """Make sure the device supports given configuration."""
    protocol = identity.identity_dict['proto']
    if protocol not in {'ssh'}:
        raise NotImplementedError(
            'Unsupported protocol: {}'.format(protocol))
    if ecdh:
        raise NotImplementedError('No support for ECDH')
    if identity.curve_name not in {formats.CURVE_NIST256}:
        raise NotImplementedError(
            'Unsupported elliptic curve: {}'.format(identity.curve_name))


class KeepKey(trezor.Trezor):
    """Connection to KeepKey device."""

    @classmethod
    def package_name(cls):
        """Python package name (at PyPI)."""
        return 'keepkey-agent'

    @property
    def _defs(self):
        from . import keepkey_defs
        return keepkey_defs

    required_version = '>=1.0.4'

    def _override_state_handler(self, _):
        """No support for `state` handling on Keepkey."""

    def pubkey(self, identity, ecdh=False):
        """Return public key."""
        _verify_support(identity, ecdh)
        return trezor.Trezor.pubkey(self, identity=identity, ecdh=ecdh)

    def ecdh(self, identity, pubkey):
        """No support for ECDH in KeepKey firmware."""
        _verify_support(identity, ecdh=True)
