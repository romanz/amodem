"""Jade-related code (see https://www.keepkey.com/)."""

import logging

import ecdsa
import semver

from .. import formats, util
from . import interface

log = logging.getLogger(__name__)


def _verify_support(identity, ecdh):
    """Make sure the device supports given configuration."""
    if identity.get_curve_name(ecdh=ecdh) != formats.CURVE_NIST256:
        raise NotImplementedError(
            'Unsupported elliptic curve: {}'.format(identity.curve_name))


class BlockstreamJade(interface.Device):
    """Connection to Blockstream Jade device."""

    MIN_SUPPORTED_FW_VERSION = semver.VersionInfo(0, 1, 33)
    DEVICE_IDS = [(0x10c4, 0xea60), (0x1a86, 0x55d4)]
    connection = None

    @classmethod
    def package_name(cls):
        """Python package name (at PyPI)."""
        return 'jade-agent'

    def connect(self):
        """Connect to the first matching device."""
        # pylint: disable=import-error
        from jadepy import JadeAPI
        from serial.tools import list_ports

        # Return the existing connection if we have one
        if BlockstreamJade.connection is not None:
            return BlockstreamJade.connection

        # Jade is a serial (over usb) device, it shows as a serial/com port device.
        # Scan com ports looking for the relevant vid and pid, and connect to the
        # first matching device.  Then call 'auth_user' - this usually requires network
        # access in order to unlock the device with a PIN and the remote blind pinserver.
        for devinfo in list_ports.comports():
            device_product_key = (devinfo.vid, devinfo.pid)
            if device_product_key in self.DEVICE_IDS:
                try:
                    jade = JadeAPI.create_serial(devinfo.device)

                    # Monkey-patch a no-op 'close()' method to suppress logged errors
                    jade.close = lambda: log.debug("Close called")

                    # Connect and fetch version info
                    jade.connect()
                    verinfo = jade.get_version_info()

                    # Check minimum supported firmware version (ignore candidate/build parts)
                    fwversion = semver.VersionInfo.parse(verinfo['JADE_VERSION'])
                    if self.MIN_SUPPORTED_FW_VERSION > fwversion.finalize_version():
                        msg = ('Outdated {} firmware for device. Please update using'
                               ' a Blockstream Green companion app')
                        raise ValueError(msg.format(fwversion))

                    # Authenticate the user (unlock with pin)
                    # NOTE: usually requires network access unless already unlocked
                    # (or temporary 'Emergency Restore' wallet is already in use).
                    network = 'testnet' if verinfo.get('JADE_NETWORKS') == 'TEST' else 'mainnet'
                    while not jade.auth_user(network):
                        log.warning("PIN incorrect, please try again")

                    # Cache the connection to jade
                    BlockstreamJade.connection = jade
                    return jade
                except Exception as e:
                    raise interface.NotFoundError(
                        '{} not connected: "{}"'.format(self, e))
        return None

    @staticmethod
    def _get_identity_string(identity):
        return interface.identity_to_string(identity.identity_dict)

    @staticmethod
    def _load_uncompressed_pubkey(pubkey, curve_name):
        assert curve_name == formats.CURVE_NIST256
        assert len(pubkey) == 65 and pubkey[0] == 0x04
        curve = ecdsa.NIST256p
        point = ecdsa.ellipticcurve.Point(curve.curve,
                                          util.bytes2num(pubkey[1:33]),
                                          util.bytes2num(pubkey[33:65]))
        return ecdsa.VerifyingKey.from_public_point(point, curve=curve,
                                                    hashfunc=formats.hashfunc)

    def pubkey(self, identity, ecdh=False):
        """Get PublicKey object for specified BIP32 address and elliptic curve."""
        _verify_support(identity, ecdh)
        identity_string = self._get_identity_string(identity)
        curve_name = identity.get_curve_name(ecdh=ecdh)
        key_type = 'slip-0017' if ecdh else 'slip-0013'

        log.debug('"%s" getting %s public key (%s) from %s',
                  identity_string, key_type, curve_name, self)
        result = self.conn.get_identity_pubkey(identity_string, curve_name, key_type)
        log.debug('result: %s', result)

        assert len(result) == 33 or len(result) == 65
        convert_pubkey = (formats.decompress_pubkey
                          if len(result) == 33 else
                          self._load_uncompressed_pubkey)
        return convert_pubkey(pubkey=result, curve_name=curve_name)

    def sign(self, identity, blob):
        """Sign given blob and return the signature (as bytes)."""
        _verify_support(identity, ecdh=False)
        identity_string = self._get_identity_string(identity)
        curve_name = identity.get_curve_name(ecdh=False)

        log.debug('"%s" signing %r (%s) on %s',
                  identity_string, blob, curve_name, self)
        result = self.conn.sign_identity(identity_string, curve_name, blob)
        log.debug('result: %s', result)

        signature = result['signature']
        assert len(signature) == 64 or (len(signature) == 65 and signature[0] == 0x00)
        if len(signature) == 65:
            signature = signature[1:]
        return signature

    def ecdh(self, identity, pubkey):
        """Get shared session key using Elliptic Curve Diffie-Hellman."""
        _verify_support(identity, ecdh=True)
        identity_string = self._get_identity_string(identity)
        curve_name = identity.get_curve_name(ecdh=True)

        log.debug('"%s" shared session key (%s) for %r from %s',
                  identity_string, curve_name, pubkey, self)
        result = self.conn.get_identity_shared_key(identity_string, curve_name, pubkey)
        log.debug('result: %s', result)

        return result
