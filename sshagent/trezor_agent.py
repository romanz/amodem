import os
import re
import sys
import argparse
import subprocess

from . import trezor
from . import server
from . import formats

import logging
log = logging.getLogger(__name__)


def identity_from_gitconfig():
    out = subprocess.check_output(args='git config --list --local'.split())
    config = dict(line.split('=', 1) for line in out.split())

    name_regex = re.compile(r'^remote\..*\.trezor$')
    names = [k for k in config if name_regex.match(k)]
    assert len(names) == 1
    key_name, = names

    section_name, _ = key_name.rsplit('.', 1)  # extract remote name marked as TREZOR's
    url = config[section_name + '.url']
    log.info('using %s=%s from git-config', key_name, url)
    user, url = url.split('@', 1)
    host, path = url.split(':', 1)
    return 'ssh://{0}@{1}/{2}'.format(user, host, path)


def main():
    fmt = '%(asctime)s %(levelname)-12s %(message)-100s [%(filename)s:%(lineno)d]'
    p = argparse.ArgumentParser()
    p.add_argument('-v', '--verbose', default=0, action='count')

    p.add_argument('identity', type=str, default=None,
                   help='proto://[user@]host[:port][/path]')

    g = p.add_mutually_exclusive_group()
    g.add_argument('-s', '--shell', default=False, action='store_true',
                   help='run $SHELL as subprocess under SSH agent')
    g.add_argument('-c', '--connect', default=False, action='store_true',
                   help='connect to specified host via SSH')
    p.add_argument('command', type=str, nargs='*', metavar='ARGUMENT',
                   help='command to run under the SSH agent')
    args = p.parse_args()

    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(args.verbose, len(levels) - 1)]
    logging.basicConfig(level=level, format=fmt)

    with trezor.Client(factory=trezor.TrezorLibrary) as client:

        label = args.identity
        command = args.command

        if label == 'git':
            label = identity_from_gitconfig()
            if command:
                command = ['git'] + command

        identity = client.get_identity(label=label)
        public_key = client.get_public_key(identity=identity)

        use_shell = False
        if args.connect:
            to_ascii = lambda s: s.encode('ascii')
            command = ['ssh', to_ascii(identity.host)]
            if identity.user:
                command += ['-l', to_ascii(identity.user)]
            if identity.port:
                command += ['-p', to_ascii(identity.port)]
            log.debug('SSH connect: %r', command)
            command = args.command + command

        if args.shell:
            command, use_shell = os.environ['SHELL'], True
            log.debug('using shell: %r', command)

        if not command:
            sys.stdout.write(public_key)
            return

        def signer(label, blob):
            identity = client.get_identity(label=label)
            return client.sign_ssh_challenge(identity=identity, blob=blob)

        try:
            with server.serve(public_keys=[public_key], signer=signer) as env:
                return server.run_process(command=command, environ=env,
                                          use_shell=use_shell)
        except KeyboardInterrupt:
            log.info('server stopped')
