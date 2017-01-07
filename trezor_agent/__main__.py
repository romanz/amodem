"""SSH-agent implementation using hardware authentication devices."""
import argparse
import functools
import logging
import os
import re
import subprocess
import sys

from . import client, device, formats, protocol, server, util

log = logging.getLogger(__name__)


def ssh_args(label):
    """Create SSH command for connecting specified server."""
    identity = device.interface.string_to_identity(label)

    args = []
    if 'port' in identity:
        args += ['-p', identity['port']]
    if 'user' in identity:
        args += ['-l', identity['user']]

    return args + [identity['host']]


def mosh_args(label):
    """Create SSH command for connecting specified server."""
    identity = device.interface.string_to_identity(label)

    args = []
    if 'port' in identity:
        args += ['-p', identity['port']]
    if 'user' in identity:
        args += [identity['user']+'@'+identity['host']]
    else:
        args += [identity['host']]

    return args


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
    g.add_argument('--mosh', default=False, action='store_true',
                   help='connect to specified host via using Mosh')

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


def run_server(conn, command, debug, timeout):
    """Common code for run_agent and run_git below."""
    try:
        handler = protocol.Handler(conn=conn, debug=debug)
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


def parse_config(fname):
    """Parse config file into a list of Identity objects."""
    contents = open(fname).read()
    for identity_str, curve_name in re.findall(r'\<(.*?)\|(.*?)\>', contents):
        yield device.interface.Identity(identity_str=identity_str,
                                        curve_name=curve_name)


class JustInTimeConnection(object):
    """Connect to the device just before the needed operation."""

    def __init__(self, conn_factory, identities):
        """Create a JIT connection object."""
        self.conn_factory = conn_factory
        self.identities = identities

    def public_keys(self):
        """Return a list of SSH public keys (in textual format)."""
        conn = self.conn_factory()
        return [conn.get_public_key(i) for i in self.identities]

    def parse_public_keys(self):
        """Parse SSH public keys into dictionaries."""
        public_keys = [formats.import_public_key(pk)
                       for pk in self.public_keys()]
        for pk, identity in zip(public_keys, self.identities):
            pk['identity'] = identity
        return public_keys

    def sign(self, blob, identity):
        """Sign a given blob using the specified identity on the device."""
        conn = self.conn_factory()
        return conn.sign_ssh_challenge(blob=blob, identity=identity)


@handle_connection_error
def run_agent(client_factory=client.Client):
    """Run ssh-agent using given hardware client factory."""
    args = create_agent_parser().parse_args()
    util.setup_logging(verbosity=args.verbose)

    if args.identity.startswith('/'):
        identities = list(parse_config(fname=args.identity))
    else:
        identities = [device.interface.Identity(
            identity_str=args.identity, curve_name=args.ecdsa_curve_name)]
    for index, identity in enumerate(identities):
        identity.identity_dict['proto'] = 'ssh'
        log.info('identity #%d: %s', index, identity)

    if args.connect:
        command = ['ssh'] + ssh_args(args.identity) + args.command
    elif args.mosh:
        command = ['mosh'] + mosh_args(args.identity) + args.command
    else:
        command = args.command

    use_shell = bool(args.shell)
    if use_shell:
        command = os.environ['SHELL']

    conn = JustInTimeConnection(
        conn_factory=lambda: client_factory(device.detect()),
        identities=identities)
    if command:
        return run_server(conn=conn, command=command, debug=args.debug,
                          timeout=args.timeout)
    else:
        for pk in conn.public_keys():
            sys.stdout.write(pk)
