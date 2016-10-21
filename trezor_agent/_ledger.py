"""TREZOR-like interface for Ledger hardware wallet."""
import binascii
import struct

from trezorlib.types_pb2 import IdentityType  # pylint: disable=import-error,unused-import
from . import util


class LedgerClientConnection(object):
    """Mock for TREZOR-like connection object."""

    def __init__(self, dongle):
        """Create connection."""
        self.dongle = dongle

    @staticmethod
    def expand_path(path):
        """Convert BIP32 path into bytes."""
        return b''.join((struct.pack('>I', e) for e in path))

    @staticmethod
    def convert_public_key(ecdsa_curve_name, result):
        """Convert Ledger reply into PublicKey object."""
        from trezorlib.messages_pb2 import PublicKey  # pylint: disable=import-error
        if ecdsa_curve_name == 'nist256p1':
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
            result = b'\x00' + bytes(keyY)
        publicKey = PublicKey()
        publicKey.node.public_key = bytes(result)
        return publicKey

    # pylint: disable=unused-argument
    def get_public_node(self, n, ecdsa_curve_name='secp256k1', show_display=False):
        """Get PublicKey object for specified BIP32 address and elliptic curve."""
        donglePath = LedgerClientConnection.expand_path(n)
        if ecdsa_curve_name == 'nist256p1':
            p2 = '01'
        else:
            p2 = '02'
        apdu = '800200' + p2
        apdu = binascii.unhexlify(apdu)
        apdu += bytearray([len(donglePath) + 1, len(donglePath) // 4])
        apdu += donglePath
        result = bytearray(self.dongle.exchange(bytes(apdu)))[1:]
        return LedgerClientConnection.convert_public_key(ecdsa_curve_name, result)

    # pylint: disable=too-many-locals
    def sign_identity(self, identity, challenge_hidden, challenge_visual,
                      ecdsa_curve_name='secp256k1'):
        """Sign specified challenges using secret key derived from given identity."""
        from trezorlib.messages_pb2 import SignedIdentity  # pylint: disable=import-error
        n = util.get_bip32_address(identity)
        donglePath = LedgerClientConnection.expand_path(n)
        if identity.proto == 'ssh':
            ins = '04'
            p1 = '00'
        else:
            ins = '08'
            p1 = '00'
        if ecdsa_curve_name == 'nist256p1':
            p2 = '81' if identity.proto == 'ssh' else '01'
        else:
            p2 = '82' if identity.proto == 'ssh' else '02'
        apdu = '80' + ins + p1 + p2
        apdu = binascii.unhexlify(apdu)
        apdu += bytearray([len(challenge_hidden) + len(donglePath) + 1])
        apdu += bytearray([len(donglePath) // 4]) + donglePath
        apdu += challenge_hidden
        result = bytearray(self.dongle.exchange(bytes(apdu)))
        if ecdsa_curve_name == 'nist256p1':
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
            signature.signature = b'\x00' + bytes(r) + bytes(s)
            if identity.proto == 'ssh':
                keyData = result[offset:]
                pk = LedgerClientConnection.convert_public_key(ecdsa_curve_name, keyData)
                signature.public_key = pk.node.public_key
            return signature
        else:
            signature = SignedIdentity()
            signature.signature = b'\x00' + bytes(result[0:64])
            if identity.proto == 'ssh':
                keyData = result[64:]
                pk = LedgerClientConnection.convert_public_key(ecdsa_curve_name, keyData)
                signature.public_key = pk.node.public_key
            return signature

    def get_ecdh_session_key(self, identity, peer_public_key, ecdsa_curve_name='secp256k1'):
        """Create shared secret key for GPG decryption."""
        from trezorlib.messages_pb2 import ECDHSessionKey  # pylint: disable=import-error
        n = util.get_bip32_address(identity, True)
        donglePath = LedgerClientConnection.expand_path(n)
        if ecdsa_curve_name == 'nist256p1':
            p2 = '01'
        else:
            p2 = '02'
        apdu = '800a00' + p2
        apdu = binascii.unhexlify(apdu)
        apdu += bytearray([len(peer_public_key) + len(donglePath) + 1])
        apdu += bytearray([len(donglePath) // 4]) + donglePath
        apdu += peer_public_key
        result = bytearray(self.dongle.exchange(bytes(apdu)))
        sessionKey = ECDHSessionKey()
        sessionKey.session_key = bytes(result)
        return sessionKey

    def clear_session(self):
        """Mock for TREZOR interface compatibility."""
        pass

    def close(self):
        """Close connection."""
        self.dongle.close()

    # pylint: disable=unused-argument
    # pylint: disable=no-self-use
    def ping(self, msg, button_protection=False, pin_protection=False,
             passphrase_protection=False):
        """Mock for TREZOR interface compatibility."""
        return msg


class CallException(Exception):
    """Ledger-related error (mainly for TREZOR compatibility)."""

    def __init__(self, code, message):
        """Create an error."""
        super(CallException, self).__init__()
        self.args = [code, message]
