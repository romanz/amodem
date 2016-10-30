"""KeepKey-related code (see https://www.keepkey.com/)."""

from . import interface, trezor
from .. import formats


class KeepKey(trezor.Trezor):
    """Connection to KeepKey device."""

    from . import keepkey_defs as defs

    required_version = '>=1.0.4'

    def connect(self):
        """No support for other than NIST256P elliptic curves."""
        if self.curve_name not in {formats.CURVE_NIST256}:
            fmt = 'KeepKey does not support {} curve'
            raise interface.NotFoundError(fmt.format(self.curve_name))

        return trezor.Trezor.connect(self)

    def ecdh(self, pubkey):
        """No support for ECDH in KeepKey firmware."""
        msg = 'KeepKey does not support ECDH'
        raise interface.NotFoundError(msg)
