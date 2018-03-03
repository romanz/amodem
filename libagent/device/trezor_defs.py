"""TREZOR-related definitions."""

# pylint: disable=unused-import,import-error

from trezorlib.client import CallException, PinException
from trezorlib.client import TrezorClient as Client
from trezorlib.messages import IdentityType, PassphraseAck, PinMatrixAck
from trezorlib.device import TrezorDevice
