#!/usr/bin/env python
"""A simple wrapper for Git commit/tag GPG signing."""
import logging
import subprocess as sp
import sys

from . import signer

log = logging.getLogger(__name__)


def main():
    """Main function."""
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')

    log.debug('sys.argv: %s', sys.argv)
    args = sys.argv[1:]
    if '--verify' in args:
        return sp.call(['gpg2'] + args)
    else:
        command = args[0]
        user_id = ' '.join(args[1:])
        assert command == '-bsau'  # --detach-sign --sign --armor --local-user
        pubkey = signer.load_from_gpg(user_id)
        s = signer.Signer.from_public_key(user_id=user_id, pubkey=pubkey)

        data = sys.stdin.read()
        sig = s.sign(data)
        sig = signer.armor(sig, 'SIGNATURE')
        sys.stdout.write(sig)
        s.close()

if __name__ == '__main__':
    main()
