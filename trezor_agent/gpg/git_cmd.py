#!/usr/bin/env python
import logging
import subprocess as sp
import sys

from . import signer

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
        s = signer.load_from_gpg(user_id)

        data = sys.stdin.read()
        sig = s.sign(data)
        sig = signer.armor(sig, 'SIGNATURE')
        sys.stdout.write(sig)
        s.close()

if __name__ == '__main__':
    main()
