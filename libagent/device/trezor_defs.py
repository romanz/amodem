"""TREZOR-related definitions."""

# pylint: disable=unused-import,import-error,no-name-in-module,no-member
import os
import logging

import mnemonic
import semver
import trezorlib

log = logging.getLogger(__name__)


if semver.match(trezorlib.__version__, ">=0.11.0"):
    from trezorlib.client import TrezorClient as Client
    from trezorlib.exceptions import TrezorFailure, PinException
    from trezorlib.transport import get_transport
    from trezorlib.messages import IdentityType

    from trezorlib.btc import get_public_node
    from trezorlib.misc import sign_identity, get_ecdh_session_key

else:
    from trezorlib.client import (TrezorClient, PinException,
                                  CallException as TrezorFailure)
    from trezorlib.messages import IdentityType
    from trezorlib import messages
    from trezorlib.transport import get_transport

    get_public_node = TrezorClient.get_public_node
    sign_identity = TrezorClient.sign_identity
    get_ecdh_session_key = TrezorClient.get_ecdh_session_key

    class Client(TrezorClient):
        """Compatibility wrapper for older TrezorClient type.

        This class redirects callback_* style methods to the UI implementation,
        and stores state so that we can reuse it.
        """

        def __init__(self, transport, ui, state=None):
            """C-tor."""
            super().__init__(transport, state=state)
            self.ui = ui

        def callback_PinMatrixRequest(self, msg):
            """Redirect PinMatrixRequest to UI."""
            try:
                pin = self.ui.get_pin(msg.type)
                if not pin.isdigit():
                    raise PinException(
                        None, 'Invalid scrambled PIN: {!r}'.format(pin))
                return messages.PinMatrixAck(pin=pin)
            except:  # noqa
                self.init_device()
                raise

        def callback_PassphraseRequest(self, msg):
            """Redirect PassphraseRequest to UI."""
            try:
                if msg.on_device is True:
                    return messages.PassphraseAck()

                passphrase = self.ui.get_passphrase()
                passphrase = mnemonic.Mnemonic.normalize_string(passphrase)

                length = len(passphrase)
                if length > 50:
                    msg = 'Too long passphrase ({} chars)'.format(length)
                    raise ValueError(msg)

                return messages.PassphraseAck(passphrase=passphrase)
            except:  # noqa
                self.init_device()
                raise

        def callback_PassphraseStateRequest(self, msg):
            """Store state provided by device so that we can reuse it later."""
            self.state = msg.state  # pylint: disable=attribute-defined-outside-init
            return messages.PassphraseStateAck()


def find_device():
    """Selects a transport based on `TREZOR_PATH` environment variable.

    If unset, picks first connected device.
    """
    try:
        return get_transport(os.environ.get("TREZOR_PATH"))
    except Exception as e:  # pylint: disable=broad-except
        log.debug("Failed to find a Trezor device: %s", e)
