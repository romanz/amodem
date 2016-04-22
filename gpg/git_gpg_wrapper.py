#!/usr/bin/env python
import sys
import subprocess as sp
import time
import logging
import os

import signer

log = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')

    log.debug('sys.argv: %s', sys.argv)
    args = sys.argv[1:]
    if '--verify' in args:
        return sp.call(['gpg2'] + args)
    else:
        command, user_id = args
        assert command == '-bsau'  # --detach-sign --sign --armor --local-user
        pubkey = signer.load_from_gpg(user_id)
        s = signer.Signer(user_id=user_id, created=pubkey['created'])
        assert s.key_id() == pubkey['key_id']

        data = sys.stdin.read()
        sig = s.sign(data)
        sig = signer.armor(sig, 'SIGNATURE')
        sys.stdout.write(sig)
        s.close()

if __name__ == '__main__':
    main()
