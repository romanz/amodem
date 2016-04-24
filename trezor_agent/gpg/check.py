#!/usr/bin/env python
"""Check GPG v2 signature for a given public key."""
import argparse
import base64
import io
import logging

from . import decode
from .. import util

log = logging.getLogger(__name__)


def original_data(filename):
    """Locate and load original file data, whose signature is provided."""
    parts = filename.rsplit('.', 1)
    if len(parts) == 2 and parts[1] in ('sig', 'asc'):
        log.debug('loading file %s', parts[0])
        return open(parts[0], 'rb').read()


def verify(pubkey, sig_file):
    """Verify correctness of public key and signature."""
    stream = open(sig_file, 'rb')
    if stream.name.endswith('.asc'):
        lines = stream.readlines()[3:-1]
        data = base64.b64decode(''.join(lines))
        payload, checksum = data[:-3], data[-3:]
        assert util.crc24(payload) == checksum
        stream = io.BytesIO(payload)
    parser = decode.Parser(util.Reader(stream), original_data(sig_file))
    signature, = list(parser)
    decode.verify_digest(pubkey=pubkey, digest=signature['digest'],
                         signature=signature['sig'], label='GPG signature')
    log.info('%s OK', sig_file)


def main():
    """Main function."""
    p = argparse.ArgumentParser()
    p.add_argument('pubkey')
    p.add_argument('signature')
    p.add_argument('-v', '--verbose', action='store_true', default=False)
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')
    verify(pubkey=decode.load_public_key(open(args.pubkey, 'rb')),
           sig_file=args.signature)

if __name__ == '__main__':
    main()
