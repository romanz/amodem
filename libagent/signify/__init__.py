"""TREZOR support for Ed25519 signify/minisign signatures."""

import argparse
import binascii
import hashlib
import logging
import sys
import time

from .. import util
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


ALG_SIGNIFY = b'Ed'
ALG_MINISIGN = b'ED'  # prehashes the data before signing


def format_payload(pubkey, data, sig_alg):
    """See http://www.openbsd.org/papers/bsdcan-signify.html for details."""
    keynum = hashlib.sha256(pubkey).digest()[:8]
    return binascii.b2a_base64(sig_alg + keynum + data).decode("ascii")


def run_pubkey(device_type, args):
    """Export hardware-based Signify public key."""
    util.setup_logging(verbosity=args.verbose)
    log.warning('This Signify tool is still in EXPERIMENTAL mode, '
                'so please note that the key derivation, API, and features '
                'may change without backwards compatibility!')

    identity = _create_identity(user_id=args.user_id)
    pubkey = Client(device=device_type()).pubkey(identity=identity)
    comment = f'untrusted comment: identity {identity.to_string()}\n'
    payload = format_payload(pubkey=pubkey, data=pubkey, sig_alg=ALG_SIGNIFY)
    print(comment + payload, end="")


def run_sign(device_type, args):
    """Prehash & sign an input blob using Ed25519."""
    util.setup_logging(verbosity=args.verbose)
    identity = _create_identity(user_id=args.user_id)

    data_to_sign = sys.stdin.buffer.read()
    sig_alg = ALG_SIGNIFY
    if args.prehash:
        # See https://github.com/jedisct1/minisign/commit/6e1023d20758b6fdb2a4b697213b0bf608ba4020
        # Released in https://github.com/jedisct1/minisign/releases/tag/0.6
        sig_alg = ALG_MINISIGN
        data_to_sign = hashlib.blake2b(data_to_sign).digest()

    sig, pubkey = Client(device=device_type()).sign_with_pubkey(identity, data_to_sign)
    pubkey_str = format_payload(pubkey=pubkey, data=pubkey, sig_alg=sig_alg)
    sig_str = format_payload(pubkey=pubkey, data=sig, sig_alg=sig_alg)
    untrusted_comment = f'untrusted comment: pubkey {pubkey_str}'
    print(untrusted_comment + sig_str, end="")

    comment_to_sign = sig + args.comment.encode()
    sig, _ = Client(device=device_type()).sign_with_pubkey(identity, comment_to_sign)
    sig_str = binascii.b2a_base64(sig).decode("ascii")
    print(f'trusted comment: {args.comment}\n' + sig_str, end="")


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
    p.add_argument('-c', '--comment', default=time.asctime())
    p.add_argument('-H', '--prehash', default=False, action='store_true')
    p.set_defaults(func=run_sign)

    args = parser.parse_args()
    device_type.ui = ui.UI(device_type=device_type, config=vars(args))
    device_type.ui.cached_passphrase_ack = util.ExpiringCache(seconds=float(60))

    return args.func(device_type=device_type, args=args)
