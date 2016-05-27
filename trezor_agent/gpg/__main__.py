#!/usr/bin/env python
"""Create signatures and export public keys for GPG using TREZOR."""
import argparse
import contextlib
import logging
import sys
import time
import os

from . import decode, encode, keyring, proto

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


def run_sign(args):
    """Generate a GPG signature using hardware-based device."""
    pubkey = decode.load_public_key(keyring.export_public_key(user_id=None),
                                    use_custom=True)
    f = encode.Factory.from_public_key(pubkey=pubkey,
                                       user_id=pubkey['user_id'])
    with contextlib.closing(f):
        if args.filename:
            data = open(args.filename, 'rb').read()
        else:
            data = sys.stdin.read()
        sig = f.sign_message(data)

    sig = proto.armor(sig, 'SIGNATURE').encode('ascii')
    decode.verify(pubkey=pubkey, signature=sig, original_data=data)

    filename = '-'  # write to stdout
    if args.output:
        filename = args.output
    elif args.filename:
        filename = args.filename + '.asc'

    if filename == '-':
        output = sys.stdout
    else:
        output = open(filename, 'wb')

    output.write(sig)


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

    sign = subparsers.add_parser('sign')
    sign.add_argument('filename', nargs='?',
                      help='Use stdin, if not specified.')
    sign.add_argument('-o', '--output', default=None,
                      help='Use stdout, if equals to "-".')
    sign.set_defaults(run=run_sign)

    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')
    args.run(args)


if __name__ == '__main__':
    main()
