#!/usr/bin/env python
"""Check GPG v2 signature for a given public key."""
import argparse
import logging

from . import decode
from .. import util

log = logging.getLogger(__name__)


def main():
    """Main function."""
    p = argparse.ArgumentParser()
    p.add_argument('pubkey')
    p.add_argument('-v', '--verbose', action='store_true', default=False)
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')
    stream = open(args.pubkey, 'rb')
    parser = decode.parse_packets(util.Reader(stream))
    pubkey, userid, sig1, subkey, sig2 = parser

    digest = decode.digest_packets([pubkey, userid, sig1])
    assert sig1['hash_prefix'] == digest[:2]
    decode.verify_digest(
        pubkey=pubkey, digest=digest,
        signature=sig1['sig'], label='GPG public key (self sig)')

    digest = decode.digest_packets([pubkey, subkey, sig2])
    assert sig2['hash_prefix'] == digest[:2]
    decode.verify_digest(
        pubkey=pubkey, digest=digest,
        signature=sig2['sig'], label='GPG subkey (1st sig)')

    sig3, = sig2['embedded']
    digest = decode.digest_packets([pubkey, subkey, sig3])
    decode.verify_digest(
        pubkey=subkey, digest=digest,
        signature=sig3['sig'], label='GPG subkey (2nd sig)')

if __name__ == '__main__':
    main()
