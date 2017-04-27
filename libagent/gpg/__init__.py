"""
TREZOR support for ECDSA GPG signatures.

See these links for more details:
 - https://www.gnupg.org/faq/whats-new-in-2.1.html
 - https://tools.ietf.org/html/rfc4880
 - https://tools.ietf.org/html/rfc6637
 - https://tools.ietf.org/html/draft-irtf-cfrg-eddsa-05
"""

import argparse
import contextlib
import logging
import os
import sys
import time

import semver

from . import agent, client, encode, keyring, protocol
from .. import device, formats, server, util

log = logging.getLogger(__name__)


def export_public_key(device_type, args):
    """Generate a new pubkey for a new/existing GPG identity."""
    log.warning('NOTE: in order to re-generate the exact same GPG key later, '
                'run this command with "--time=%d" commandline flag (to set '
                'the timestamp of the GPG key manually).', args.time)
    c = client.Client(user_id=args.user_id, curve_name=args.ecdsa_curve,
                      device_type=device_type)
    verifying_key = c.pubkey(ecdh=False)
    decryption_key = c.pubkey(ecdh=True)

    if args.subkey:  # add as subkey
        log.info('adding %s GPG subkey for "%s" to existing key',
                 args.ecdsa_curve, args.user_id)
        # subkey for signing
        signing_key = protocol.PublicKey(
            curve_name=args.ecdsa_curve, created=args.time,
            verifying_key=verifying_key, ecdh=False)
        # subkey for encryption
        encryption_key = protocol.PublicKey(
            curve_name=formats.get_ecdh_curve_name(args.ecdsa_curve),
            created=args.time, verifying_key=decryption_key, ecdh=True)
        primary_bytes = keyring.export_public_key(args.user_id)
        result = encode.create_subkey(primary_bytes=primary_bytes,
                                      subkey=signing_key,
                                      signer_func=c.sign)
        result = encode.create_subkey(primary_bytes=result,
                                      subkey=encryption_key,
                                      signer_func=c.sign)
    else:  # add as primary
        log.info('creating new %s GPG primary key for "%s"',
                 args.ecdsa_curve, args.user_id)
        # primary key for signing
        primary = protocol.PublicKey(
            curve_name=args.ecdsa_curve, created=args.time,
            verifying_key=verifying_key, ecdh=False)
        # subkey for encryption
        subkey = protocol.PublicKey(
            curve_name=formats.get_ecdh_curve_name(args.ecdsa_curve),
            created=args.time, verifying_key=decryption_key, ecdh=True)

        result = encode.create_primary(user_id=args.user_id,
                                       pubkey=primary,
                                       signer_func=c.sign)
        result = encode.create_subkey(primary_bytes=result,
                                      subkey=subkey,
                                      signer_func=c.sign)

    sys.stdout.write(protocol.armor(result, 'PUBLIC KEY BLOCK'))


def run_create(device_type, args):
    """Export public GPG key."""
    util.setup_logging(verbosity=args.verbose)
    log.warning('This GPG tool is still in EXPERIMENTAL mode, '
                'so please note that the API and features may '
                'change without backwards compatibility!')

    existing_gpg = keyring.gpg_version().decode('ascii')
    required_gpg = '>=2.1.11'
    if semver.match(existing_gpg, required_gpg):
        export_public_key(device_type, args)
    else:
        log.error('Existing gpg2 has version "%s" (%s required)',
                  existing_gpg, required_gpg)


def run_unlock(device_type, args):
    """Unlock hardware device (for future interaction)."""
    util.setup_logging(verbosity=args.verbose)
    with device_type() as d:
        log.info('unlocked %s device', d)


def run_agent(device_type):
    """Run a simple GPG-agent server."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--homedir', default=os.environ.get('GNUPGHOME'))
    args, _ = parser.parse_known_args()

    assert args.homedir
    config_file = os.path.join(args.homedir, 'gpg-agent.conf')

    lines = (line.strip() for line in open(config_file))
    lines = (line for line in lines if line and not line.startswith('#'))
    config = dict(line.split(' ', 1) for line in lines)

    util.setup_logging(verbosity=int(config['verbosity']),
                       filename=config['log-file'])
    sock_path = keyring.get_agent_sock_path()
    with server.unix_domain_socket_server(sock_path) as sock:
        for conn in agent.yield_connections(sock):
            with contextlib.closing(conn):
                try:
                    agent.handle_connection(conn=conn, device_type=device_type)
                except StopIteration:
                    log.info('stopping gpg-agent')
                    return
                except Exception as e:  # pylint: disable=broad-except
                    log.exception('gpg-agent failed: %s', e)


def main(device_type):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    p = subparsers.add_parser('create', help='Export public GPG key')
    p.add_argument('user_id')
    p.add_argument('-e', '--ecdsa-curve', default='nist256p1')
    p.add_argument('-t', '--time', type=int, default=int(time.time()))
    p.add_argument('-v', '--verbose', default=0, action='count')
    p.add_argument('-s', '--subkey', default=False, action='store_true')
    p.set_defaults(func=run_create)

    p = subparsers.add_parser('unlock', help='Unlock the hardware device')
    p.add_argument('-v', '--verbose', default=0, action='count')
    p.set_defaults(func=run_unlock)

    args = parser.parse_args()
    return args.func(device_type=device_type, args=args)
