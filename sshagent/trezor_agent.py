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
    p.add_argument('-v', '--verbose', default=0, action='count')

    p.add_argument('-i', '--identity', type=str,
                   help='proto://[user@]host[:port][/path]')

    g = p.add_mutually_exclusive_group()
    g.add_argument('-s', '--shell', default=False, action='store_true',
                   help='run $SHELL as subprocess under SSH agent')
    g.add_argument('-c', '--connect', default=False, action='store_true',
                   help='connect to specified host via SSH')
    p.add_argument('argument', type=str, nargs='*', metavar='ARGUMENT',
                   help='command to run under the SSH agent')
    args = p.parse_args()

    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(args.verbose, len(levels))]
    logging.basicConfig(level=level, format=fmt)

    with trezor.Client(factory=trezor.TrezorLibrary) as client:
        identity = client.get_identity(label=args.identity)
        public_key = client.get_public_key(identity=identity)

        command, use_shell = args.argument, False
        if args.connect:
            to_ascii = lambda s: s.encode('ascii')
            command = ['ssh', to_ascii(identity.host)]
            if identity.user:
                command += ['-l', to_ascii(identity.user)]
            if identity.port:
                command += ['-p', to_ascii(identity.port)]
            log.debug('SSH connect: %r', command)

        if args.shell:
            command, use_shell = os.environ['SHELL'], True
            log.debug('using shell: %r', command)

        if not command:
            sys.stdout.write(public_key)
            return

        signer = client.sign_ssh_challenge

        try:
            with server.serve(public_keys=[public_key], signer=signer) as env:
                return server.run_process(command=command, environ=env,
                                          use_shell=use_shell)
        except KeyboardInterrupt:
            log.info('server stopped')
