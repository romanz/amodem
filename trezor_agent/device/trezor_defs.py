"""TREZOR-related definitions."""

# pylint: disable=unused-import
from trezorlib.client import TrezorClient as Client
from trezorlib.client import CallException
from trezorlib.transport_hid import HidTransport
from trezorlib.messages_pb2 import PassphraseAck
from trezorlib.types_pb2 import IdentityType
