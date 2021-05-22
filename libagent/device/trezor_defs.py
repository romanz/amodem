"""TREZOR-related definitions."""

import logging
# pylint: disable=unused-import,import-error,no-name-in-module,no-member
import os

import mnemonic
import semver

import trezorlib
from trezorlib.btc import get_address, get_public_node
from trezorlib.client import PASSPHRASE_TEST_PATH
from trezorlib.client import TrezorClient as Client
from trezorlib.exceptions import PinException, TrezorFailure
from trezorlib.messages import IdentityType
from trezorlib.misc import get_ecdh_session_key, sign_identity
from trezorlib.transport import get_transport

log = logging.getLogger(__name__)


def find_device():
    """Selects a transport based on `TREZOR_PATH` environment variable.

    If unset, picks first connected device.
    """
    try:
        return get_transport(os.environ.get("TREZOR_PATH"))
    except Exception as e:  # pylint: disable=broad-except
        log.debug("Failed to find a Trezor device: %s", e)
        return None
