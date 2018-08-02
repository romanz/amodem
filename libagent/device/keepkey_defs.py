"""KeepKey-related definitions."""

# pylint: disable=unused-import,import-error

from keepkeylib.client import CallException, PinException
from keepkeylib.client import KeepKeyClient as Client
from keepkeylib.messages_pb2 import PassphraseAck, PinMatrixAck
from keepkeylib.transport_hid import HidTransport
from keepkeylib.types_pb2 import IdentityType


def find_device():
    """Returns first USB HID transport."""
    return next(HidTransport(p) for p in HidTransport.enumerate())
