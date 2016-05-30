#!/usr/bin/env python
"""Create signatures and export public keys for GPG using TREZOR."""
import argparse
import contextlib
import logging
import os
import sys
import time

from . import encode, keyring, proto

log = logging.getLogger(__name__)


def run_create(args):
    """Generate a new pubkey for a new/existing GPG identity."""
    user_id = os.environ['TREZOR_GPG_USER_ID']
    f = encode.Factory(user_id=user_id, created=args.time,
                       curve_name=args.ecdsa_curve)

    with contextlib.closing(f):
        if args.subkey:
            primary_key = keyring.export_public_key(user_id=user_id)
            result = f.create_subkey(primary_bytes=primary_key)
        else:
            result = f.create_primary()

    sys.stdout.write(proto.armor(result, 'PUBLIC KEY BLOCK'))


def main():
    """Main function."""
    p = argparse.ArgumentParser()
    p.add_argument('-v', '--verbose', action='store_true', default=False)
    subparsers = p.add_subparsers()
    subparsers.required = True
    subparsers.dest = 'command'

    create = subparsers.add_parser('create')
    create.add_argument('-s', '--subkey', action='store_true', default=False)
    create.add_argument('-e', '--ecdsa-curve', default='nist256p1')
    create.add_argument('-t', '--time', type=int, default=int(time.time()))
    create.set_defaults(run=run_create)

    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')
    args.run(args)


if __name__ == '__main__':
    main()
