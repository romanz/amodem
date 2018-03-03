"""TREZOR-related definitions."""

# pylint: disable=unused-import,import-error

from trezorlib.client import CallException, PinException
from trezorlib.client import TrezorClient as Client
from trezorlib.messages import IdentityType, PassphraseAck, PinMatrixAck
from trezorlib.device import TrezorDevice


def enumerate_transports():
    """Returns all available transports."""
    return TrezorDevice.enumerate()
