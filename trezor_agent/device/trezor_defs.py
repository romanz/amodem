"""TREZOR-related definitions."""

# pylint: disable=unused-import

from trezorlib.client import CallException as Error
from trezorlib.client import TrezorClient as Client
from trezorlib.messages_pb2 import PassphraseAck
from trezorlib.transport_hid import HidTransport
from trezorlib.types_pb2 import IdentityType
