"""TREZOR-related code (see http://bitcointrezor.com/)."""

import binascii
import logging
import os

import semver

from . import interface

log = logging.getLogger(__name__)


class Trezor(interface.Device):
    """Connection to TREZOR device."""

    @property
    def _defs(self):
        from . import trezor_defs
        return trezor_defs

    required_version = '>=1.4.0'
    passphrase = os.environ.get('TREZOR_PASSPHRASE', '')

    def connect(self):
        """Enumerate and connect to the first USB HID interface."""
        def passphrase_handler(_):
            log.debug('using %s passphrase for %s',
                      'non-empty' if self.passphrase else 'empty', self)
            return self._defs.PassphraseAck(passphrase=self.passphrase)

        for d in self._defs.HidTransport.enumerate():
            log.debug('endpoint: %s', d)
            transport = self._defs.HidTransport(d)
            connection = self._defs.Client(transport)
            connection.callback_PassphraseRequest = passphrase_handler
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
            connection.ping(msg='', pin_protection=True)  # unlock PIN
            return connection
        raise interface.NotFoundError('{} not connected'.format(self))

    def close(self):
        """Close connection."""
        self.conn.close()

    def pubkey(self, identity, ecdh=False):
        """Return public key."""
        curve_name = identity.get_curve_name(ecdh=ecdh)
        log.debug('"%s" getting public key (%s) from %s',
                  identity, curve_name, self)
        addr = identity.get_bip32_address(ecdh=ecdh)
        result = self.conn.get_public_node(n=addr,
                                           ecdsa_curve_name=curve_name)
        log.debug('result: %s', result)
        return result.node.public_key

    def _identity_proto(self, identity):
        result = self._defs.IdentityType()
        for name, value in identity.items():
            setattr(result, name, value)
        return result

    def sign(self, identity, blob):
        """Sign given blob and return the signature (as bytes)."""
        curve_name = identity.get_curve_name(ecdh=False)
        log.debug('"%s" signing %r (%s) on %s',
                  identity, blob, curve_name, self)
        try:
            result = self.conn.sign_identity(
                identity=self._identity_proto(identity),
                challenge_hidden=blob,
                challenge_visual='',
                ecdsa_curve_name=curve_name)
            log.debug('result: %s', result)
            assert len(result.signature) == 65
            assert result.signature[:1] == b'\x00'
            return result.signature[1:]
        except self._defs.Error as e:
            msg = '{} error: {}'.format(self, e)
            log.debug(msg, exc_info=True)
            raise interface.DeviceError(msg)

    def ecdh(self, identity, pubkey):
        """Get shared session key using Elliptic Curve Diffie-Hellman."""
        curve_name = identity.get_curve_name(ecdh=True)
        log.debug('"%s" shared session key (%s) for %r from %s',
                  identity, curve_name, pubkey, self)
        try:
            result = self.conn.get_ecdh_session_key(
                identity=self._identity_proto(identity),
                peer_public_key=pubkey,
                ecdsa_curve_name=curve_name)
            log.debug('result: %s', result)
            assert len(result.session_key) in {65, 33}  # NIST256 or Curve25519
            assert result.session_key[:1] == b'\x04'
            return result.session_key
        except self._defs.Error as e:
            msg = '{} error: {}'.format(self, e)
            log.debug(msg, exc_info=True)
            raise interface.DeviceError(msg)
