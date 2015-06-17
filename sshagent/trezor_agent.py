import sys
import argparse

from . import trezor
from . import server
from . import formats

import logging
log = logging.getLogger(__name__)


def main():
    fmt = '%(asctime)s %(levelname)-12s %(message)-100s [%(filename)s]'
    p = argparse.ArgumentParser()
    p.add_argument('-k', '--key-label',
                   metavar='LABEL', dest='labels', action='append', default=[])
    p.add_argument('-v', '--verbose', action='count', default=0)
    p.add_argument('command', type=str, nargs='*')
    args = p.parse_args()

    verbosity = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = verbosity[min(args.verbose, len(verbosity) - 1)]
    logging.basicConfig(level=level, format=fmt)

    with trezor.Client(factory=trezor.TrezorLibrary) as client:
        key_files = []
        for label in args.labels:
            pubkey = client.get_public_key(label=label)
            key_file = formats.export_public_key(pubkey=pubkey, label=label)
            key_files.append(key_file)

        if not args.command:
            sys.stdout.write(''.join(key_files))
            return

        signer = client.sign_ssh_challenge

        try:
            with server.serve(key_files=key_files, signer=signer) as env:
                return server.run_process(command=args.command, environ=env)
        except KeyboardInterrupt:
            log.info('server stopped')

if __name__ == '__main__':
    sys.exit(main())
