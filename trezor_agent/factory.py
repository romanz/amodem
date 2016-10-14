"""Thin wrapper around trezor/keepkey libraries."""
from __future__ import absolute_import
import binascii
import collections
import logging

import semver

from . import util

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
    import struct

    class LedgerClientConnection(object):
        def __init__(self, dongle):
            self.dongle = dongle

        @staticmethod
        def expand_path(path):
            result = ""
            for pathElement in path:
                result = result + struct.pack(">I", pathElement)
            return result

        @staticmethod
        def convert_public_key(ecdsa_curve_name, result):
            from trezorlib.messages_pb2 import PublicKey  # pylint: disable=import-error
            if ecdsa_curve_name == "nist256p1":
                if (result[64] & 1) != 0:
                    result = bytearray([0x03]) + result[1:33]
                else:
                    result = bytearray([0x02]) + result[1:33]
            else:
                result = result[1:]
                keyX = bytearray(result[0:32])
                keyY = bytearray(result[32:][::-1])
                if (keyX[31] & 1) != 0:
                    keyY[31] |= 0x80
                result = chr(0) + str(keyY)
            publicKey = PublicKey()
            publicKey.node.public_key = str(result)
            return publicKey

        # pylint: disable=unused-argument
        def get_public_node(self, n, ecdsa_curve_name="secp256k1", show_display=False):
            donglePath = LedgerClientConnection.expand_path(n)
            if ecdsa_curve_name == "nist256p1":
                p2 = "01"
            else:
                p2 = "02"
            apdu = "800200" + p2
            apdu = apdu.decode('hex')
            apdu += chr(len(donglePath) + 1) + chr(len(donglePath) / 4)
            apdu += donglePath
            result = bytearray(self.dongle.exchange(bytes(apdu)))[1:]
            return LedgerClientConnection.convert_public_key(ecdsa_curve_name, result)

        # pylint: disable=too-many-locals
        def sign_identity(self, identity, challenge_hidden, challenge_visual,
                          ecdsa_curve_name="secp256k1"):
            from trezorlib.messages_pb2 import SignedIdentity  # pylint: disable=import-error
            n = util.get_bip32_address(identity)
            donglePath = LedgerClientConnection.expand_path(n)
            if identity.proto == 'ssh':
                ins = "04"
                p1 = "00"
            else:
                ins = "08"
                p1 = "00"
            if ecdsa_curve_name == "nist256p1":
                p2 = "81" if identity.proto == 'ssh' else "01"
            else:
                p2 = "82" if identity.proto == 'ssh' else "02"
            apdu = "80" + ins + p1 + p2
            apdu = apdu.decode('hex')
            apdu += chr(len(challenge_hidden) + len(donglePath) + 1)
            apdu += chr(len(donglePath) / 4) + donglePath
            apdu += challenge_hidden
            result = bytearray(self.dongle.exchange(bytes(apdu)))
            if ecdsa_curve_name == "nist256p1":
                offset = 3
                length = result[offset]
                r = result[offset+1:offset+1+length]
                if r[0] == 0:
                    r = r[1:]
                offset = offset + 1 + length + 1
                length = result[offset]
                s = result[offset+1:offset+1+length]
                if s[0] == 0:
                    s = s[1:]
                offset = offset + 1 + length
                signature = SignedIdentity()
                signature.signature = chr(0) + str(r) + str(s)
                if identity.proto == 'ssh':
                    keyData = result[offset:]
                    pk = LedgerClientConnection.convert_public_key(ecdsa_curve_name, keyData)
                    signature.public_key = pk.node.public_key
                return signature
            else:
                signature = SignedIdentity()
                signature.signature = chr(0) + str(result[0:64])
                if identity.proto == 'ssh':
                    keyData = result[64:]
                    pk = LedgerClientConnection.convert_public_key(ecdsa_curve_name, keyData)
                    signature.public_key = pk.node.public_key
                return signature

        def get_ecdh_session_key(self, identity, peer_public_key, ecdsa_curve_name="secp256k1"):
            from trezorlib.messages_pb2 import ECDHSessionKey  # pylint: disable=import-error
            n = util.get_bip32_address(identity, True)
            donglePath = LedgerClientConnection.expand_path(n)
            if ecdsa_curve_name == "nist256p1":
                p2 = "01"
            else:
                p2 = "02"
            apdu = "800a00" + p2
            apdu = apdu.decode('hex')
            apdu += chr(len(peer_public_key) + len(donglePath) + 1)
            apdu += chr(len(donglePath) / 4) + donglePath
            apdu += peer_public_key
            result = bytearray(self.dongle.exchange(bytes(apdu)))
            sessionKey = ECDHSessionKey()
            sessionKey.session_key = str(result)
            return sessionKey

        def clear_session(self):
            pass

        def close(self):
            self.dongle.close()

        # pylint: disable=unused-argument
        # pylint: disable=no-self-use
        def ping(self, msg, button_protection=False, pin_protection=False,
                 passphrase_protection=False):
            return msg

    class CallException(Exception):
        def __init__(self, code, message):
            super(CallException, self).__init__()
            self.args = [code, message]
    try:
        from ledgerblue.comm import getDongle
    except ImportError as e:
        log.warning('%s: install via "pip install ledgerblue" '
                    'if you need to support this device', e)
        return
    # pylint: disable=bare-except
    try:
        from trezorlib.types_pb2 import IdentityType  # pylint: disable=import-error
        dongle = getDongle()
    except:
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
