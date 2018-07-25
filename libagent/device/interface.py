"""Device abstraction layer."""

import hashlib
import io
import logging
import re
import struct

import unidecode

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


class Error(Exception):
    """Device-related error."""


class NotFoundError(Error):
    """Device could not be found."""


class DeviceError(Error):
    """Error during device operation."""


class Identity:
    """Represent SLIP-0013 identity, together with a elliptic curve choice."""

    def __init__(self, identity_str, curve_name):
        """Configure for specific identity and elliptic curve usage."""
        self.identity_dict = string_to_identity(identity_str)
        self.curve_name = curve_name

    def items(self):
        """Return a copy of identity_dict items."""
        return [(k, unidecode.unidecode(v))
                for k, v in self.identity_dict.items()]

    def to_bytes(self):
        """Transliterate Unicode into ASCII."""
        s = identity_to_string(self.identity_dict)
        return unidecode.unidecode(s).encode('ascii')

    def to_string(self):
        """Return identity serialized to string."""
        return u'<{}|{}>'.format(identity_to_string(self.identity_dict), self.curve_name)

    def get_bip32_address(self, ecdh=False):
        """Compute BIP32 derivation address according to SLIP-0013/0017."""
        index = struct.pack('<L', self.identity_dict.get('index', 0))
        addr = index + self.to_bytes()
        log.debug('bip32 address string: %r', addr)
        digest = hashlib.sha256(addr).digest()
        s = io.BytesIO(bytearray(digest))

        hardened = 0x80000000
        addr_0 = 17 if bool(ecdh) else 13
        address_n = [addr_0] + list(util.recv(s, '<LLLL'))
        return [(hardened | value) for value in address_n]

    def get_curve_name(self, ecdh=False):
        """Return correct curve name for device operations."""
        if ecdh:
            return formats.get_ecdh_curve_name(self.curve_name)
        else:
            return self.curve_name


class Device:
    """Abstract cryptographic hardware device interface."""

    def __init__(self):
        """C-tor."""
        self.conn = None

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

    def pubkey(self, identity, ecdh=False):
        """Get public key (as bytes)."""
        raise NotImplementedError()

    def sign(self, identity, blob):
        """Sign given blob and return the signature (as bytes)."""
        raise NotImplementedError()

    def ecdh(self, identity, pubkey):
        """Get shared session key using Elliptic Curve Diffie-Hellman."""
        raise NotImplementedError()

    def __str__(self):
        """Human-readable representation."""
        return '{}'.format(self.__class__.__name__)
