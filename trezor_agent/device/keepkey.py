"""KeepKey-related code (see https://www.keepkey.com/)."""

from . import interface, trezor


class KeepKey(trezor.Trezor):
    """Connection to KeepKey device."""

    from . import keepkey_defs as defs

    required_version = '>=1.0.4'

    def ecdh(self, identity, pubkey):
        """No support for ECDH in KeepKey firmware."""
        msg = 'KeepKey does not support ECDH'
        raise interface.NotFoundError(msg)
