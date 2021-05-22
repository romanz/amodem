"""TREZOR support for Ed25519 signify signatures."""

import argparse
import binascii
import contextlib
import functools
import hashlib
import logging
import os
import re
import struct
import subprocess
import sys
import time

import pkg_resources
import semver

from .. import formats, server, util
from ..device import interface, ui

log = logging.getLogger(__name__)


def _create_identity(user_id):
    result = interface.Identity(identity_str='signify://', curve_name='ed25519')
    result.identity_dict['host'] = user_id
    return result


class Client:
    """Sign messages and get public keys from a hardware device."""

    def __init__(self, device):
        """C-tor."""
        self.device = device

    def pubkey(self, identity):
        """Return public key as VerifyingKey object."""
        with self.device:
            return bytes(self.device.pubkey(ecdh=False, identity=identity))

    def sign_with_pubkey(self, identity, data):
        """Sign the data and return a signature."""
        log.info('please confirm Signify signature on %s for "%s"...',
                 self.device, identity.to_string())
        log.debug('signing data: %s', util.hexlify(data))
        with self.device:
            sig, pubkey = self.device.sign_with_pubkey(blob=data, identity=identity)
            assert len(sig) == 64
            assert len(pubkey) == 33
            assert pubkey[:1] == b"\x00"
            return sig, pubkey[1:]


def format_payload(pubkey, data):
    """See http://www.openbsd.org/papers/bsdcan-signify.html for details."""
    keynum = hashlib.sha256(pubkey).digest()[:8]
    return binascii.b2a_base64(b"Ed" + keynum + data).decode("ascii")


def run_pubkey(device_type, args):
    """Export hardware-based Signify public key."""
    util.setup_logging(verbosity=args.verbose)
    log.warning('This Signify tool is still in EXPERIMENTAL mode, '
                'so please note that the key derivation, API, and features '
                'may change without backwards compatibility!')

    identity = _create_identity(user_id=args.user_id)
    pubkey = Client(device=device_type()).pubkey(identity=identity)
    comment = f'untrusted comment: identity {identity.to_string()}\n'
    result = comment + format_payload(pubkey=pubkey, data=pubkey)
    print(result, end="")


def run_sign(device_type, args):
    """Sign an input blob using Ed25519."""
    util.setup_logging(verbosity=args.verbose)
    identity = _create_identity(user_id=args.user_id)
    data = sys.stdin.buffer.read()
    sig, pubkey = Client(device=device_type()).sign_with_pubkey(identity, data)
    pubkey_str = format_payload(pubkey=pubkey, data=pubkey)
    comment = f'untrusted comment: pubkey {pubkey_str}'
    result = comment + format_payload(pubkey=pubkey, data=sig)
    print(result, end="")


def main(device_type):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(title='Action', dest='action')
    subparsers.required = True

    p = subparsers.add_parser('pubkey')
    p.add_argument('user_id')
    p.add_argument('-v', '--verbose', default=0, action='count')
    p.set_defaults(func=run_pubkey)

    p = subparsers.add_parser('sign')
    p.add_argument('user_id')
    p.add_argument('-v', '--verbose', default=0, action='count')
    p.set_defaults(func=run_sign)

    args = parser.parse_args()
    device_type.ui = ui.UI(device_type=device_type, config=vars(args))
    device_type.ui.cached_passphrase_ack = util.ExpiringCache(seconds=float(60))

    return args.func(device_type=device_type, args=args)
