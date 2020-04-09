"""TREZOR-related definitions."""

# pylint: disable=unused-import,import-error,no-name-in-module,no-member
import os
import logging

import mnemonic
import semver
import trezorlib

from trezorlib.client import TrezorClient as Client, PASSPHRASE_TEST_PATH
from trezorlib.exceptions import TrezorFailure, PinException
from trezorlib.transport import get_transport
from trezorlib.messages import IdentityType

from trezorlib.btc import get_address, get_public_node
from trezorlib.misc import sign_identity, get_ecdh_session_key

log = logging.getLogger(__name__)


def find_device():
    """Selects a transport based on `TREZOR_PATH` environment variable.

    If unset, picks first connected device.
    """
    try:
        return get_transport(os.environ.get("TREZOR_PATH"))
    except Exception as e:  # pylint: disable=broad-except
        log.debug("Failed to find a Trezor device: %s", e)
