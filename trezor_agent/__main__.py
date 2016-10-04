"""SSH-agent implementation using hardware authentication devices."""
import argparse
import functools
import logging
import os
import re
import subprocess
import sys

from . import client, formats, protocol, server, util

log = logging.getLogger(__name__)


def ssh_args(label):
    """Create SSH command for connecting specified server."""
    identity = util.string_to_identity(label, identity_type=dict)

    args = []
    if 'port' in identity:
        args += ['-p', identity['port']]
    if 'user' in identity:
        args += ['-l', identity['user']]

    return ['ssh'] + args + [identity['host']]


def create_parser():
    """Create argparse.ArgumentParser for this tool."""
    p = argparse.ArgumentParser()
    p.add_argument('-v', '--verbose', default=0, action='count')

    curve_names = [name for name in formats.SUPPORTED_CURVES]
    curve_names = ', '.join(sorted(curve_names))
    p.add_argument('-e', '--ecdsa-curve-name', metavar='CURVE',
                   default=formats.CURVE_NIST256,
                   help='specify ECDSA curve name: ' + curve_names)
    p.add_argument('--timeout',
                   default=server.UNIX_SOCKET_TIMEOUT, type=float,
                   help='Timeout for accepting SSH client connections')
    p.add_argument('--debug', default=False, action='store_true',
                   help='Log SSH protocol messages for debugging.')
    return p


def create_agent_parser():
    """Specific parser for SSH connection."""
    p = create_parser()

    g = p.add_mutually_exclusive_group()
    g.add_argument('-s', '--shell', default=False, action='store_true',
                   help='run ${SHELL} as subprocess under SSH agent')
    g.add_argument('-c', '--connect', default=False, action='store_true',
                   help='connect to specified host via SSH')

    p.add_argument('identity', type=str, default=None,
                   help='proto://[user@]host[:port][/path]')
    p.add_argument('command', type=str, nargs='*', metavar='ARGUMENT',
                   help='command to run under the SSH agent')
    return p


def create_git_parser():
    """Specific parser for git commands."""
    p = create_parser()

    p.add_argument('-r', '--remote', default='origin',
                   help='use this git remote URL to generate SSH identity')
    p.add_argument('-t', '--test', action='store_true',
                   help='test connection using `ssh -T user@host` command')
    p.add_argument('command', type=str, nargs='*', metavar='ARGUMENT',
                   help='Git command to run under the SSH agent')
    return p


def setup_logging(verbosity):
    """Configure logging for this tool."""
    fmt = ('%(asctime)s %(levelname)-12s %(message)-100s '
           '[%(filename)s:%(lineno)d]')
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbosity, len(levels) - 1)]
    logging.basicConfig(format=fmt, level=level)


def git_host(remote_name, attributes):
    """Extract git SSH host for specified remote name."""
    try:
        output = subprocess.check_output('git config --local --list'.split())
    except subprocess.CalledProcessError:
        return

    for attribute in attributes:
        name = r'remote.{0}.{1}'.format(remote_name, attribute)
        matches = re.findall(re.escape(name) + '=(.*)', output)
        log.debug('%r: %r', name, matches)
        if not matches:
            continue

        url = matches[0].strip()
        match = re.match('(?P<user>.*?)@(?P<host>.*?):(?P<path>.*)', url)
        if match:
            return '{user}@{host}'.format(**match.groupdict())


def run_server(conn, public_key, command, debug, timeout):
    """Common code for run_agent and run_git below."""
    try:
        signer = conn.sign_ssh_challenge
        public_key = formats.import_public_key(public_key)
        log.info('using SSH public key: %s', public_key['fingerprint'])
        handler = protocol.Handler(keys=[public_key], signer=signer,
                                   debug=debug)
        with server.serve(handler=handler, timeout=timeout) as env:
            return server.run_process(command=command, environ=env)
    except KeyboardInterrupt:
        log.info('server stopped')


def handle_connection_error(func):
    """Fail with non-zero exit code."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IOError as e:
            log.error('Connection error: %s', e)
            return 1
    return wrapper


@handle_connection_error
def run_agent(client_factory=client.Client):
    """Run ssh-agent using given hardware client factory."""
    args = create_agent_parser().parse_args()
    setup_logging(verbosity=args.verbose)

    with client_factory(curve=args.ecdsa_curve_name) as conn:
        label = args.identity
        command = args.command

        public_key = conn.get_public_key(label=label)

        if args.connect:
            command = ssh_args(label) + args.command
            log.debug('SSH connect: %r', command)

        use_shell = bool(args.shell)
        if use_shell:
            command = os.environ['SHELL']
            log.debug('using shell: %r', command)

        if not command:
            sys.stdout.write(public_key)
            return

        return run_server(conn=conn, public_key=public_key, command=command,
                          debug=args.debug, timeout=args.timeout)


@handle_connection_error
def run_git(client_factory=client.Client):
    """Run git under ssh-agent using given hardware client factory."""
    args = create_git_parser().parse_args()
    setup_logging(verbosity=args.verbose)

    with client_factory(curve=args.ecdsa_curve_name) as conn:
        label = git_host(args.remote, ['pushurl', 'url'])
        if not label:
            log.error('Could not find "%s" SSH remote in .git/config',
                      args.remote)
            return

        public_key = conn.get_public_key(label=label)

        if not args.test:
            if args.command:
                command = ['git'] + args.command
            else:
                sys.stdout.write(public_key)
                return
        else:
            command = ['ssh', '-T', label]

        return run_server(conn=conn, public_key=public_key, command=command,
                          debug=args.debug, timeout=args.timeout)
