#!/usr/bin/env python
import sys
import subprocess as sp
import time
import logging
import os

import signer

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-10s %(message)s')

def main():
    args = sys.argv[1:]
    if '--verify' in args:
        sp.check_call(['gpg2'] + args)
    else:
        user_id = os.environ['GPG_USER_ID']
        user_id = user_id.encode('ascii')
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
