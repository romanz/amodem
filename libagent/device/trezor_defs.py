"""TREZOR-related definitions."""

# pylint: disable=unused-import,import-error
import os
import logging

from trezorlib.client import CallException, PinException
from trezorlib.client import TrezorClient as Client
from trezorlib.messages import IdentityType, PassphraseAck, PinMatrixAck, PassphraseStateAck

try:
    from trezorlib.transport import get_transport
except ImportError:
    from trezorlib.device import TrezorDevice
    get_transport = TrezorDevice.find_by_path

log = logging.getLogger(__name__)


def find_device():
    """Selects a transport based on `TREZOR_PATH` environment variable.

    If unset, picks first connected device.
    """
    try:
        return get_transport(os.environ.get("TREZOR_PATH"))
    except Exception as e:  # pylint: disable=broad-except
        log.debug("Failed to find a Trezor device: %s", e)
