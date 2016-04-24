#!/usr/bin/env python
"""Create signatures and export public keys for GPG using TREZOR."""
import argparse
import logging
import time

from . import check, decode, encode

log = logging.getLogger(__name__)


def main():
    """Main function."""
    p = argparse.ArgumentParser()
    p.add_argument('user_id')
    p.add_argument('filename', nargs='?')
    p.add_argument('-t', '--time', type=int, default=int(time.time()))
    p.add_argument('-a', '--armor', action='store_true', default=False)
    p.add_argument('-v', '--verbose', action='store_true', default=False)
    p.add_argument('-e', '--ecdsa-curve', default='nist256p1')

    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')
    user_id = args.user_id.encode('ascii')
    if not args.filename:
        s = encode.Signer(user_id=user_id, created=args.time,
                          curve_name=args.ecdsa_curve)
        pubkey = s.export()
        ext = '.pub'
        if args.armor:
            pubkey = encode.armor(pubkey, 'PUBLIC KEY BLOCK')
            ext = '.asc'
        filename = s.hex_short_key_id() + ext
        open(filename, 'wb').write(pubkey)
        log.info('import to local keyring using "gpg2 --import %s"', filename)
    else:
        pubkey = decode.load_from_gpg(user_id)
        s = encode.Signer.from_public_key(pubkey=pubkey, user_id=user_id)
        data = open(args.filename, 'rb').read()
        sig, ext = s.sign(data), '.sig'
        if args.armor:
            sig = encode.armor(sig, 'SIGNATURE')
            ext = '.asc'
        filename = args.filename + ext
        open(filename, 'wb').write(sig)
        check.verify(pubkey=pubkey, sig_file=filename)

    s.close()


if __name__ == '__main__':
    main()
