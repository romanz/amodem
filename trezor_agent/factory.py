"""Thin wrapper around trezor/keepkey libraries."""
from __future__ import absolute_import

import binascii
import collections
import logging

import semver

log = logging.getLogger(__name__)

ClientWrapper = collections.namedtuple(
    'ClientWrapper',
    ['connection', 'identity_type', 'device_name', 'call_exception'])


# pylint: disable=too-many-arguments
def _load_client(name, client_type, hid_transport,
                 passphrase_ack, identity_type,
                 required_version, call_exception):

    def empty_passphrase_handler(_):
        return passphrase_ack(passphrase='')

    for d in hid_transport.enumerate():
        connection = client_type(hid_transport(d))
        connection.callback_PassphraseRequest = empty_passphrase_handler
        f = connection.features
        log.debug('connected to %s %s', name, f.device_id)
        log.debug('label    : %s', f.label)
        log.debug('vendor   : %s', f.vendor)
        current_version = '{}.{}.{}'.format(f.major_version,
                                            f.minor_version,
                                            f.patch_version)
        log.debug('version  : %s', current_version)
        log.debug('revision : %s', binascii.hexlify(f.revision))
        if not semver.match(current_version, required_version):
            fmt = 'Please upgrade your {} firmware to {} version (current: {})'
            raise ValueError(fmt.format(name,
                                        required_version,
                                        current_version))
        yield ClientWrapper(connection=connection,
                            identity_type=identity_type,
                            device_name=name,
                            call_exception=call_exception)
        return


def _load_trezor():
    try:
        from trezorlib.client import TrezorClient, CallException
        from trezorlib.transport_hid import HidTransport
        from trezorlib.messages_pb2 import PassphraseAck
        from trezorlib.types_pb2 import IdentityType
        return _load_client(name='Trezor',
                            client_type=TrezorClient,
                            hid_transport=HidTransport,
                            passphrase_ack=PassphraseAck,
                            identity_type=IdentityType,
                            required_version='>=1.4.0',
                            call_exception=CallException)
    except ImportError as e:
        log.warning('%s: install via "pip install trezor" '
                    'if you need to support this device', e)


def _load_keepkey():
    try:
        from keepkeylib.client import KeepKeyClient, CallException
        from keepkeylib.transport_hid import HidTransport
        from keepkeylib.messages_pb2 import PassphraseAck
        from keepkeylib.types_pb2 import IdentityType
        return _load_client(name='KeepKey',
                            client_type=KeepKeyClient,
                            hid_transport=HidTransport,
                            passphrase_ack=PassphraseAck,
                            identity_type=IdentityType,
                            required_version='>=1.0.4',
                            call_exception=CallException)
    except ImportError as e:
        log.warning('%s: install via "pip install keepkey" '
                    'if you need to support this device', e)


def _load_ledger():
    from ._ledger import LedgerClientConnection, CallException, IdentityType
    try:
        from ledgerblue.comm import getDongle, CommException
    except ImportError as e:
        log.warning('%s: install via "pip install ledgerblue" '
                    'if you need to support this device', e)
        return
    try:
        dongle = getDongle()
    except CommException:
        return

    yield ClientWrapper(connection=LedgerClientConnection(dongle),
                        identity_type=IdentityType,
                        device_name="ledger",
                        call_exception=CallException)


LOADERS = [
    _load_trezor,
    _load_keepkey,
    _load_ledger
]


def load(loaders=None):
    """Load a single device, via specified loaders' list."""
    loaders = loaders if loaders is not None else LOADERS
    device_list = []
    for loader in loaders:
        device = loader()
        if device:
            device_list.extend(device)

    if len(device_list) == 1:
        return device_list[0]

    msg = '{:d} devices found'.format(len(device_list))
    raise IOError(msg)
