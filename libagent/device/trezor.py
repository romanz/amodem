"""TREZOR-related code (see http://bitcointrezor.com/)."""

import binascii
import logging
import os
import subprocess
import sys

import semver

from . import interface

log = logging.getLogger(__name__)


def _message_box(label, sp=subprocess):
    """Launch an external process for PIN/passphrase entry GUI."""
    cmd = ('import sys, pymsgbox; '
           'sys.stdout.write(pymsgbox.password(sys.stdin.read()))')
    args = [sys.executable, '-c', cmd]
    p = sp.Popen(args=args, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    out, err = p.communicate(label.encode('ascii'))
    exitcode = p.wait()
    if exitcode != 0:
        log.error('UI failed: %r', err)
        raise sp.CalledProcessError(exitcode, args)
    return out.decode('ascii')


def _is_open_tty(stream):
    return not stream.closed and os.isatty(stream.fileno())


class Trezor(interface.Device):
    """Connection to TREZOR device."""

    @classmethod
    def package_name(cls):
        """Python package name (at PyPI)."""
        return 'trezor-agent'

    @property
    def _defs(self):
        from . import trezor_defs
        # Allow using TREZOR bridge transport (instead of the HID default)
        trezor_defs.Transport = {
            'bridge': trezor_defs.BridgeTransport,
            'udp': trezor_defs.UdpTransport,
            'hid': trezor_defs.HidTransport,
        }[os.environ.get('TREZOR_TRANSPORT', 'hid')]
        return trezor_defs

    required_version = '>=1.4.0'

    def _override_pin_handler(self, conn):
        cli_handler = conn.callback_PinMatrixRequest

        def new_handler(msg):
            if _is_open_tty(sys.stdin):
                result = cli_handler(msg)  # CLI-based PIN handler
            else:
                scrambled_pin = _message_box(
                    'Use the numeric keypad to describe number positions.\n'
                    'The layout is:\n'
                    '    7 8 9\n'
                    '    4 5 6\n'
                    '    1 2 3\n'
                    'Please enter PIN:')
                result = self._defs.PinMatrixAck(pin=scrambled_pin)
            if not set(result.pin).issubset('123456789'):
                raise self._defs.PinException(
                    None, 'Invalid scrambled PIN: {!r}'.format(result.pin))
            return result

        conn.callback_PinMatrixRequest = new_handler

    def _override_passphrase_handler(self, conn):
        cli_handler = conn.callback_PassphraseRequest

        def new_handler(msg):
            if _is_open_tty(sys.stdin):
                return cli_handler(msg)  # CLI-based PIN handler

            passphrase = _message_box('Please enter passphrase:')
            return self._defs.PassphraseAck(passphrase=passphrase)

        conn.callback_PassphraseRequest = new_handler

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
        """Enumerate and connect to the first USB HID interface."""
        for transport in self._defs.Transport.enumerate():
            log.debug('transport: %s', transport)
            for _ in range(5):
                connection = self._defs.Client(transport)
                self._override_pin_handler(connection)
                self._override_passphrase_handler(connection)
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

        raise interface.NotFoundError('{} not connected'.format(self))

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
