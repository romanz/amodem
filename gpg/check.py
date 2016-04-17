#!/usr/bin/env python
import argparse
import base64
import io
import logging

import decode
import util

log = logging.getLogger(__name__)


def original_data(filename):
    parts = filename.rsplit('.', 1)
    if len(parts) == 2 and parts[1] in ('sig', 'asc'):
        log.debug('loading file %s', parts[0])
        return open(parts[0], 'rb').read()


def check(pubkey, sig_file):
    d = open(sig_file, 'rb')
    if d.name.endswith('.asc'):
        lines = d.readlines()[3:-1]
        data = base64.b64decode(''.join(lines))
        payload, checksum = data[:-3], data[-3:]
        assert util.crc24(payload) == checksum
        d = io.BytesIO(payload)
    parser = decode.Parser(decode.Reader(d), original_data(sig_file))
    signature, = list(parser)
    decode.verify_digest(pubkey=pubkey, digest=signature['digest'],
                         signature=signature['sig'], label='GPG signature')


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')
    p = argparse.ArgumentParser()
    p.add_argument('pubkey')
    p.add_argument('signature')
    args = p.parse_args()
    check(pubkey=decode.load_public_key(open(args.pubkey, 'rb')),
          sig_file=args.signature)

if __name__ == '__main__':
    main()
