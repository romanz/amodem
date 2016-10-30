"""Device abstraction layer."""

import hashlib
import io
import logging
import re
import struct

from .. import formats, util

log = logging.getLogger(__name__)

_identity_regexp = re.compile(''.join([
    '^'
    r'(?:(?P<proto>.*)://)?',
    r'(?:(?P<user>.*)@)?',
    r'(?P<host>.*?)',
    r'(?::(?P<port>\w*))?',
    r'(?P<path>/.*)?',
    '$'
]))


def string_to_identity(identity_str):
    """Parse string into Identity dictionary."""
    m = _identity_regexp.match(identity_str)
    result = m.groupdict()
    log.debug('parsed identity: %s', result)
    return {k: v for k, v in result.items() if v}


def identity_to_string(identity_dict):
    """Dump Identity dictionary into its string representation."""
    result = []
    if identity_dict.get('proto'):
        result.append(identity_dict['proto'] + '://')
    if identity_dict.get('user'):
        result.append(identity_dict['user'] + '@')
    result.append(identity_dict['host'])
    if identity_dict.get('port'):
        result.append(':' + identity_dict['port'])
    if identity_dict.get('path'):
        result.append(identity_dict['path'])
    log.debug('identity parts: %s', result)
    return ''.join(result)


def get_bip32_address(identity_dict, ecdh=False):
    """Compute BIP32 derivation address according to SLIP-0013/0017."""
    index = struct.pack('<L', identity_dict.get('index', 0))
    addr = index + identity_to_string(identity_dict).encode('ascii')
    log.debug('bip32 address string: %r', addr)
    digest = hashlib.sha256(addr).digest()
    s = io.BytesIO(bytearray(digest))

    hardened = 0x80000000
    addr_0 = [13, 17][bool(ecdh)]
    address_n = [addr_0] + list(util.recv(s, '<LLLL'))
    return [(hardened | value) for value in address_n]


class Error(Exception):
    """Device-related error."""


class NotFoundError(Error):
    """Device could not be found."""


class DeviceError(Error):
    """"Error during device operation."""


class Device(object):
    """Abstract cryptographic hardware device interface."""

    def __init__(self, identity_str, curve_name):
        """Configure for specific identity and elliptic curve usage."""
        self.identity_dict = string_to_identity(identity_str)
        self.curve_name = curve_name
        self.conn = None

    def identity_str(self):
        """Return identity serialized to string."""
        return identity_to_string(self.identity_dict)

    def connect(self):
        """Connect to device, otherwise raise NotFoundError."""
        raise NotImplementedError()

    def __enter__(self):
        """Allow usage as context manager."""
        self.conn = self.connect()
        return self

    def __exit__(self, *args):
        """Close and mark as disconnected."""
        try:
            self.conn.close()
        except Exception as e:  # pylint: disable=broad-except
            log.exception('close failed: %s', e)
        self.conn = None

    def pubkey(self, ecdh=False):
        """Get public key (as bytes)."""
        raise NotImplementedError()

    def sign(self, blob):
        """Sign given blob and return the signature (as bytes)."""
        raise NotImplementedError()

    def ecdh(self, pubkey):
        """Get shared session key using Elliptic Curve Diffie-Hellman."""
        raise NotImplementedError()

    def __str__(self):
        """Human-readable representation."""
        return '{}'.format(self.__class__.__name__)

    def get_curve_name(self, ecdh=False):
        """Return correct curve name for device operations."""
        if ecdh:
            return formats.get_ecdh_curve_name(self.curve_name)
        else:
            return self.curve_name
