"""TREZOR-related code (see http://bitcointrezor.com/)."""

import binascii
import logging

import mnemonic
import semver

from . import interface
from .. import util

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

    def _override_pin_handler(self, conn):
        if self.ui is None:
            return

        def new_handler(_):
            try:
                scrambled_pin = self.ui.get_pin()
                result = self._defs.PinMatrixAck(pin=scrambled_pin)
                if not set(scrambled_pin).issubset('123456789'):
                    raise self._defs.PinException(
                        None, 'Invalid scrambled PIN: {!r}'.format(result.pin))
                return result
            except:  # noqa
                conn.init_device()
                raise

        conn.callback_PinMatrixRequest = new_handler

    cached_passphrase_ack = util.ExpiringCache(seconds=float('inf'))
    cached_state = None

    def _override_passphrase_handler(self, conn):
        if self.ui is None:
            return

        def new_handler(msg):
            try:
                if msg.on_device is True:
                    return self._defs.PassphraseAck()
                ack = self.__class__.cached_passphrase_ack.get()
                if ack:
                    log.debug('re-using cached %s passphrase', self)
                    return ack

                passphrase = self.ui.get_passphrase()
                passphrase = mnemonic.Mnemonic.normalize_string(passphrase)
                ack = self._defs.PassphraseAck(passphrase=passphrase)

                length = len(ack.passphrase)
                if length > 50:
                    msg = 'Too long passphrase ({} chars)'.format(length)
                    raise ValueError(msg)

                self.__class__.cached_passphrase_ack.set(ack)
                return ack
            except:  # noqa
                conn.init_device()
                raise

        conn.callback_PassphraseRequest = new_handler

    def _override_state_handler(self, conn):
        def callback_PassphraseStateRequest(msg):
            log.debug('caching state from %r', msg)
            self.__class__.cached_state = msg.state
            return self._defs.PassphraseStateAck()

        conn.callback_PassphraseStateRequest = callback_PassphraseStateRequest

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
                                           state=self.__class__.cached_state)
            self._override_pin_handler(connection)
            self._override_passphrase_handler(connection)
            self._override_state_handler(connection)
            self._verify_version(connection)

            try:
                connection.ping(msg='', pin_protection=True)  # unlock PIN
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
        self.conn.close()

    def pubkey(self, identity, ecdh=False):
        """Return public key."""
        curve_name = identity.get_curve_name(ecdh=ecdh)
        log.debug('"%s" getting public key (%s) from %s',
                  identity.to_string(), curve_name, self)
        addr = identity.get_bip32_address(ecdh=ecdh)
        result = self.conn.get_public_node(
            n=addr, ecdsa_curve_name=curve_name)
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
            result = self.conn.sign_identity(
                identity=self._identity_proto(identity),
                challenge_hidden=blob,
                challenge_visual='',
                ecdsa_curve_name=curve_name)
            log.debug('result: %s', result)
            assert len(result.signature) == 65
            assert result.signature[:1] == b'\x00'
            return bytes(result.signature[1:])
        except self._defs.CallException as e:
            msg = '{} error: {}'.format(self, e)
            log.debug(msg, exc_info=True)
            raise interface.DeviceError(msg)

    def ecdh(self, identity, pubkey):
        """Get shared session key using Elliptic Curve Diffie-Hellman."""
        curve_name = identity.get_curve_name(ecdh=True)
        log.debug('"%s" shared session key (%s) for %r from %s',
                  identity.to_string(), curve_name, pubkey, self)
        try:
            result = self.conn.get_ecdh_session_key(
                identity=self._identity_proto(identity),
                peer_public_key=pubkey,
                ecdsa_curve_name=curve_name)
            log.debug('result: %s', result)
            assert len(result.session_key) in {65, 33}  # NIST256 or Curve25519
            assert result.session_key[:1] == b'\x04'
            return bytes(result.session_key)
        except self._defs.CallException as e:
            msg = '{} error: {}'.format(self, e)
            log.debug(msg, exc_info=True)
            raise interface.DeviceError(msg)
