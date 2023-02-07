"""Ledger-related code (see https://www.ledgerwallet.com/)."""

import binascii
import logging
import struct

from ledgerblue import comm  # pylint: disable=import-error

from .. import formats
from . import interface

log = logging.getLogger(__name__)


def _expand_path(path):
    """Convert BIP32 path into bytes."""
    return b''.join((struct.pack('>I', e) for e in path))


def _convert_public_key(ecdsa_curve_name, result):
    """Convert Ledger reply into PublicKey object."""
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
    return bytes(result)


class LedgerNanoS(interface.Device):
    """Connection to Ledger Nano S device."""

    LEDGER_APP_NAME = "SSH/PGP Agent"
    ledger_app_version = None
    ledger_app_supports_end_of_frame_byte = True

    def get_app_name_and_version(self, dongle):
        """Retrieve currently running Ledger application name and its version string."""
        device_version_answer = dongle.exchange(binascii.unhexlify('B001000000'))
        offset = 1
        app_name_length = struct.unpack_from("B", device_version_answer, offset)[0]
        offset += 1
        app_name = device_version_answer[offset: offset + app_name_length]
        offset += app_name_length
        app_version_length = struct.unpack_from("B", device_version_answer, offset)[0]
        offset += 1
        app_version = device_version_answer[offset: offset + app_version_length]
        log.debug("running app %s, version %s", app_name, app_version)
        return (app_name.decode(), app_version.decode())

    @classmethod
    def package_name(cls):
        """Python package name (at PyPI)."""
        return 'ledger-agent'

    def connect(self):
        """Enumerate and connect to the first USB HID interface."""
        try:
            dongle = comm.getDongle(debug=True)
            (app_name, self.ledger_app_version) = self.get_app_name_and_version(dongle)

            version_parts = self.ledger_app_version.split(".")
            if (version_parts[0] == "0" and version_parts[1] == "0" and int(version_parts[2]) <= 7):
                self.ledger_app_supports_end_of_frame_byte = False

            if app_name != LedgerNanoS.LEDGER_APP_NAME:
                # we could launch the app here if we are in the dashboard
                raise interface.DeviceError(f'{self} is not running {LedgerNanoS.LEDGER_APP_NAME}')

            return dongle
        except comm.CommException as e:
            raise interface.DeviceError(
                'Error ({}) communicating with {}'.format(e, self))

    def pubkey(self, identity, ecdh=False):
        """Get PublicKey object for specified BIP32 address and elliptic curve."""
        curve_name = identity.get_curve_name(ecdh)
        path = _expand_path(identity.get_bip32_address(ecdh))
        if curve_name == 'nist256p1':
            p2 = '01'
        else:
            p2 = '02'
        apdu = '800200' + p2
        apdu = binascii.unhexlify(apdu)
        apdu += bytearray([len(path) + 1, len(path) // 4])
        apdu += path
        log.debug('apdu: %r', apdu)
        result = bytearray(self.conn.exchange(bytes(apdu)))
        log.debug('result: %r', result)
        return formats.decompress_pubkey(
            pubkey=_convert_public_key(curve_name, result[1:]),
            curve_name=identity.curve_name)

    def sign(self, identity, blob):
        """Sign given blob and return the signature (as bytes)."""
        # pylint: disable=too-many-locals,too-many-branches
        path = _expand_path(identity.get_bip32_address(ecdh=False))
        offset = 0
        result = None
        while offset != len(blob):
            data = bytes()
            if offset == 0:
                data += bytearray([len(path) // 4]) + path
            chunk_size = min(len(blob) - offset, 255 - len(data))
            data += blob[offset:offset + chunk_size]

            if identity.identity_dict['proto'] == 'ssh':
                ins = '04'
            else:
                ins = '08'

            if identity.curve_name == 'nist256p1':
                p2 = '81' if identity.identity_dict['proto'] == 'ssh' else '01'
            else:
                p2 = '82' if identity.identity_dict['proto'] == 'ssh' else '02'

            if offset + chunk_size == len(blob) and self.ledger_app_supports_end_of_frame_byte:
                # mark that we are at the end of the frame
                p1 = "80" if offset == 0 else "81"
            else:
                p1 = "00" if offset == 0 else "01"

            apdu = binascii.unhexlify('80' + ins + p1 + p2) + len(data).to_bytes(1, 'little') + data

            log.debug('apdu: %r', apdu)
            try:
                result = bytearray(self.conn.exchange(bytes(apdu)))
            except comm.CommException as e:
                raise interface.DeviceError(
                    'Error ({}) communicating with {}'.format(e, self))

            offset += chunk_size

        log.debug('result: %r', result)
        if identity.curve_name == 'nist256p1':
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
            return bytes(r) + bytes(s)
        else:
            return bytes(result[:64])

    def ecdh(self, identity, pubkey):
        """Get shared session key using Elliptic Curve Diffie-Hellman."""
        path = _expand_path(identity.get_bip32_address(ecdh=True))
        if identity.curve_name == 'nist256p1':
            p2 = '01'
        else:
            p2 = '02'
        apdu = '800a00' + p2
        apdu = binascii.unhexlify(apdu)
        apdu += bytearray([len(pubkey) + len(path) + 1])
        apdu += bytearray([len(path) // 4]) + path
        apdu += pubkey
        log.debug('apdu: %r', apdu)
        try:
            result = bytearray(self.conn.exchange(bytes(apdu)))
        except comm.CommException as e:
            raise interface.DeviceError(
                'Error ({}) communicating with {}'.format(e, self))
        log.debug('result: %r', result)
        assert result[0] == 0x04
        return bytes(result)
