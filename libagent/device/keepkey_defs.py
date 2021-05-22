"""KeepKey-related definitions."""

# pylint: disable=unused-import,import-error

from keepkeylib.client import CallException
from keepkeylib.client import KeepKeyClient as Client
from keepkeylib.client import PinException
from keepkeylib.messages_pb2 import PassphraseAck, PinMatrixAck
from keepkeylib.transport_hid import HidTransport
from keepkeylib.transport_webusb import WebUsbTransport
from keepkeylib.types_pb2 import IdentityType

get_public_node = Client.get_public_node
sign_identity = Client.sign_identity
Client.state = None


def find_device():
    """Returns first WebUSB or HID transport."""
    for d in WebUsbTransport.enumerate():
        return WebUsbTransport(d)

    for d in HidTransport.enumerate():
        return HidTransport(d)
