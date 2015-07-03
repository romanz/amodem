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
    p.add_argument('-v', '--verbose', action='count', default=0,
                   help='increase the the logging verbosity')
    p.add_argument('-c', dest='command', type=str, default=None,
                   help='command to run under the SSH agent')
    p.add_argument('identity', type=str, nargs='*',
                   help='proto://[user@]host[:port][/path]')
    args = p.parse_args()

    verbosity = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = verbosity[min(args.verbose, len(verbosity) - 1)]
    logging.basicConfig(level=level, format=fmt)

    with trezor.Client(factory=trezor.TrezorLibrary) as client:
        key_files = []
        for label in args.identity:
            pubkey = client.get_public_key(label)
            key_file = formats.export_public_key(pubkey=pubkey, label=label)
            key_files.append(key_file)

        command = args.command
        if not command:
            command = os.environ['SHELL']
            log.info('using %r shell', command)

        signer = client.sign_ssh_challenge

        try:
            with server.serve(key_files=key_files, signer=signer) as env:
                return server.run_process(command=command, environ=env)
        except KeyboardInterrupt:
            log.info('server stopped')

if __name__ == '__main__':
    sys.exit(main())
