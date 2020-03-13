"""KeepKey-related definitions."""

# pylint: disable=unused-import,import-error

from keepkeylib.client import CallException, PinException
from keepkeylib.client import KeepKeyClient as Client
from keepkeylib.messages_pb2 import PassphraseAck, PinMatrixAck
from keepkeylib.transport_hid import HidTransport
from keepkeylib.transport_webusb import WebUsbTransport
from keepkeylib.types_pb2 import IdentityType


def find_device():
    """Returns first WebUSB or HID transport."""
    webusb = WebUsbTransport.enumerate()
    hidusb = HidTransport.enumerate()

    if len(webusb):
        return next(WebUsbTransport(p) for p in webusb)
    elif len(hidusb):
        return next(HidTransport(p) for p in hidusb)
