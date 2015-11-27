import os
import re
import sys
import argparse
import subprocess
import functools

from . import trezor
from . import server
from . import formats

import logging
log = logging.getLogger(__name__)


def identity_from_gitconfig():
    out = subprocess.check_output(args='git config --list --local'.split())
    config = [line.split('=', 1) for line in out.strip().split('\n')]
    config_dict = dict(item for item in config if len(item) == 2)

    name_regex = re.compile(r'^remote\..*\.trezor$')
    names = [item[0] for item in config if name_regex.match(item[0])]
    if len(names) != 1:
        log.error('please add "trezor" key '
                  'to a single remote section at .git/config')
        sys.exit(1)
    key_name = names[0]
    identity_label = config_dict.get(key_name)
    if identity_label:
        return identity_label

    # extract remote name marked as TREZOR's
    section_name, _ = key_name.rsplit('.', 1)

    key_name = section_name + '.url'
    url = config_dict[key_name]
    log.debug('using "%s=%s" from git-config', key_name, url)

    user, url = url.split('@', 1)
    host, path = url.split(':', 1)
    return 'ssh://{0}@{1}/{2}'.format(user, host, path)


def ssh_args(label):
    identity = trezor.client.string_to_identity(label, identity_type=dict)

    args = []
    if 'port' in identity:
        args += ['-p', identity['port']]
    if 'user' in identity:
        args += ['-l', identity['user']]

    return ['ssh'] + args + [identity['host']]


def create_agent_parser():
    p = argparse.ArgumentParser()
    p.add_argument('-v', '--verbose', default=0, action='count')

    p.add_argument('identity', type=str, default=None,
                   help='proto://[user@]host[:port][/path]')

    g = p.add_mutually_exclusive_group()
    g.add_argument('-s', '--shell', default=False, action='store_true',
                   help='run ${SHELL} as subprocess under SSH agent')
    g.add_argument('-c', '--connect', default=False, action='store_true',
                   help='connect to specified host via SSH')
    curves = ', '.join(sorted(formats.SUPPORTED_CURVES))
    p.add_argument('-e', '--ecdsa-curve-name', metavar='CURVE',
                   default=formats.CURVE_NIST256,
                   help='specify ECDSA curve name: ' + curves)
    p.add_argument('command', type=str, nargs='*', metavar='ARGUMENT',
                   help='command to run under the SSH agent')
    return p


def setup_logging(verbosity):
    fmt = ('%(asctime)s %(levelname)-12s %(message)-100s '
           '[%(filename)s:%(lineno)d]')
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbosity, len(levels) - 1)]
    logging.basicConfig(format=fmt, level=level)


def ssh_sign(client, label, blob):
    return client.sign_ssh_challenge(label=label, blob=blob)


def run_agent(client_factory):
    args = create_agent_parser().parse_args()
    setup_logging(verbosity=args.verbose)

    with client_factory(curve=args.ecdsa_curve_name) as client:
        label = args.identity
        command = args.command

        if label == 'git':
            label = identity_from_gitconfig()
            log.info('using identity %r for git command %r', label, command)
            if command:
                command = ['git'] + command

        public_key = client.get_public_key(label=label)

        use_shell = False
        if args.connect:
            command = ssh_args(label) + args.command
            log.debug('SSH connect: %r', command)

        if args.shell:
            command, use_shell = os.environ['SHELL'], True
            log.debug('using shell: %r', command)

        if not command:
            sys.stdout.write(public_key)
            return

        try:
            signer = functools.partial(ssh_sign, client=client)
            with server.serve(public_keys=[public_key], signer=signer) as env:
                return server.run_process(command=command, environ=env,
                                          use_shell=use_shell)
        except KeyboardInterrupt:
            log.info('server stopped')


def trezor_agent():
    run_agent(trezor.Client)
