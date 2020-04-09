"""TREZOR-related code (see http://bitcointrezor.com/)."""

import binascii
import logging

import semver

from . import interface

log = logging.getLogger(__name__)


class Trezor(interface.Device):
    """Connection to TREZOR device."""

    @classmethod
    def package_name(cls):
        """Python package name (at PyPI)."""
        return 'trezor-agent'

    @property
    def _defs(self):
        from . import trezor_defs
        return trezor_defs

    required_version = '>=1.4.0'

    ui = None  # can be overridden by device's users
    cached_session_id = None

    def _verify_version(self, connection):
        f = connection.features
        log.debug('connected to %s %s', self, f.device_id)
        log.debug('label    : %s', f.label)
        log.debug('vendor   : %s', f.vendor)
        current_version = '{}.{}.{}'.format(f.major_version,
                                            f.minor_version,
                                            f.patch_version)
        log.debug('version  : %s', current_version)
        log.debug('revision : %s', binascii.hexlify(f.revision))
        if not semver.match(current_version, self.required_version):
            fmt = ('Please upgrade your {} firmware to {} version'
                   ' (current: {})')
            raise ValueError(fmt.format(self, self.required_version,
                                        current_version))

    def connect(self):
        """Enumerate and connect to the first available interface."""
        transport = self._defs.find_device()
        if not transport:
            raise interface.NotFoundError('{} not connected'.format(self))

        log.debug('using transport: %s', transport)
        for _ in range(5):  # Retry a few times in case of PIN failures
            connection = self._defs.Client(transport=transport,
                                           ui=self.ui,
                                           session_id=self.__class__.cached_session_id)
            self._verify_version(connection)

            try:
                # unlock PIN and passphrase
                self._defs.get_address(connection,
                                       "Testnet",
                                       self._defs.PASSPHRASE_TEST_PATH)
                return connection
            except (self._defs.PinException, ValueError) as e:
                log.error('Invalid PIN: %s, retrying...', e)
                continue
            except Exception as e:
                log.exception('ping failed: %s', e)
                connection.close()  # so the next HID open() will succeed
                raise

    def close(self):
        """Close connection."""
        self.__class__.cached_session_id = self.conn.session_id
        super().close()

    def pubkey(self, identity, ecdh=False):
        """Return public key."""
        curve_name = identity.get_curve_name(ecdh=ecdh)
        log.debug('"%s" getting public key (%s) from %s',
                  identity.to_string(), curve_name, self)
        addr = identity.get_bip32_address(ecdh=ecdh)
        result = self._defs.get_public_node(
            self.conn,
            n=addr,
            ecdsa_curve_name=curve_name)
        log.debug('result: %s', result)
        return bytes(result.node.public_key)

    def _identity_proto(self, identity):
        result = self._defs.IdentityType()
        for name, value in identity.items():
            setattr(result, name, value)
        return result

    def sign(self, identity, blob):
        """Sign given blob and return the signature (as bytes)."""
        curve_name = identity.get_curve_name(ecdh=False)
        log.debug('"%s" signing %r (%s) on %s',
                  identity.to_string(), blob, curve_name, self)
        try:
            result = self._defs.sign_identity(
                self.conn,
                identity=self._identity_proto(identity),
                challenge_hidden=blob,
                challenge_visual='',
                ecdsa_curve_name=curve_name)
            log.debug('result: %s', result)
            assert len(result.signature) == 65
            assert result.signature[:1] == b'\x00'
            return bytes(result.signature[1:])
        except self._defs.TrezorFailure as e:
            msg = '{} error: {}'.format(self, e)
            log.debug(msg, exc_info=True)
            raise interface.DeviceError(msg)

    def ecdh(self, identity, pubkey):
        """Get shared session key using Elliptic Curve Diffie-Hellman."""
        curve_name = identity.get_curve_name(ecdh=True)
        log.debug('"%s" shared session key (%s) for %r from %s',
                  identity.to_string(), curve_name, pubkey, self)
        try:
            result = self._defs.get_ecdh_session_key(
                self.conn,
                identity=self._identity_proto(identity),
                peer_public_key=pubkey,
                ecdsa_curve_name=curve_name)
            log.debug('result: %s', result)
            assert len(result.session_key) in {65, 33}  # NIST256 or Curve25519
            assert result.session_key[:1] == b'\x04'
            return bytes(result.session_key)
        except self._defs.TrezorFailure as e:
            msg = '{} error: {}'.format(self, e)
            log.debug(msg, exc_info=True)
            raise interface.DeviceError(msg)
