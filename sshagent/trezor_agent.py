import os
import sys
import argparse

from . import trezor
from . import server
from . import formats

import logging
log = logging.getLogger(__name__)


def main():
    fmt = '%(asctime)s %(levelname)-12s %(message)-100s [%(filename)s:%(lineno)d]'
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument('-v', '--verbose', default=0, action='count')
    g.add_argument('-q', '--quiet', default=False, action='store_true')

    p.add_argument('-c', dest='command', type=str, default=None,
                   help='command to run under the SSH agent')
    p.add_argument('identity', type=str, nargs='*',
                   help='proto://[user@]host[:port][/path]')
    args = p.parse_args()

    loglevel = logging.INFO
    if args.verbose:
        loglevel = logging.DEBUG
    if args.quiet:
        loglevel = logging.WARNING

    logging.basicConfig(level=loglevel, format=fmt)

    with trezor.Client(factory=trezor.TrezorLibrary) as client:
        public_keys = [client.get_public_key(i) for i in args.identity]

        command = args.command
        if not command:
            command = os.environ['SHELL']
            log.info('using %r shell', command)

        signer = client.sign_ssh_challenge

        try:
            with server.serve(public_keys=public_keys, signer=signer) as env:
                return server.run_process(command=command, environ=env)
        except KeyboardInterrupt:
            log.info('server stopped')

if __name__ == '__main__':
    sys.exit(main())
