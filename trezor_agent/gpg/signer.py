#!/usr/bin/env python
"""Create signatures and export public keys for GPG using TREZOR."""
import argparse
import logging
import subprocess as sp
import sys
import time

from . import decode, encode

log = logging.getLogger(__name__)


def run_create(args):
    """Generate a new pubkey for a new/existing GPG identity."""
    s = encode.Signer(user_id=args.user_id, created=args.time,
                      curve_name=args.ecdsa_curve)
    if args.subkey:
        subkey = s.subkey()
        primary = sp.check_output(['gpg2', '--export', args.user_id])
        result = primary + subkey
    else:
        result = s.export()
    s.close()

    return encode.armor(result, 'PUBLIC KEY BLOCK')


def run_sign(args):
    """Generate a GPG signature using hardware-based device."""
    pubkey = decode.load_from_gpg(user_id=None, use_custom=True)
    s = encode.Signer.from_public_key(pubkey=pubkey, user_id=pubkey['user_id'])
    if args.filename:
        data = open(args.filename, 'rb').read()
    else:
        data = sys.stdin.read()
    sig = s.sign(data)
    s.close()

    sig = encode.armor(sig, 'SIGNATURE')
    decode.verify(pubkey=pubkey, signature=sig, original_data=data)
    return sig


def main():
    """Main function."""
    p = argparse.ArgumentParser()
    p.add_argument('-v', '--verbose', action='store_true', default=False)
    subparsers = p.add_subparsers()

    create = subparsers.add_parser('create')
    create.add_argument('user_id', help='e.g. '
                        '"Satoshi Nakamoto <satoshi@nakamoto.bit>"')
    create.add_argument('-s', '--subkey', action='store_true', default=False)
    create.add_argument('-e', '--ecdsa-curve', default='nist256p1')
    create.add_argument('-t', '--time', type=int, default=int(time.time()))
    create.set_defaults(run=run_create)

    sign = subparsers.add_parser('sign')
    sign.add_argument('filename', nargs='?')
    sign.set_defaults(run=run_sign)

    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')
    result = args.run(args)
    sys.stdout.write(result)


if __name__ == '__main__':
    main()
