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

    p.add_argument('-p', '--public-key', default=False, action='store_true')

    p.add_argument('-i', '--identity', type=str,
                   help='proto://[user@]host[:port][/path]')
    p.add_argument('command', type=str, nargs='*',
                   help='command to run under the SSH agent')
    args = p.parse_args()

    loglevel = logging.INFO
    if args.verbose:
        loglevel = logging.DEBUG
    if args.quiet:
        loglevel = logging.WARNING

    logging.basicConfig(level=loglevel, format=fmt)

    with trezor.Client(factory=trezor.TrezorLibrary) as client:
        identity = client.get_identity(label=args.identity)
        public_key = client.get_public_key(identity=identity)
        if args.public_key:
            sys.stdout.write(public_key)
            return

        command, use_shell = args.command, False
        if not command:
            command, use_shell = os.environ['SHELL'], True

        signer = client.sign_ssh_challenge

        try:
            with server.serve(public_keys=[public_key], signer=signer) as env:
                return server.run_process(
                    command=command, environ=env, use_shell=use_shell
                )
        except KeyboardInterrupt:
            log.info('server stopped')
