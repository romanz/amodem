#!/usr/bin/env python
"""Create signatures and export public keys for GPG using TREZOR."""
import argparse
import contextlib
import logging
import sys
import time

import semver

from . import agent, device, encode, keyring, protocol
from .. import formats, server, util

log = logging.getLogger(__name__)


def run_create(args):
    """Generate a new pubkey for a new/existing GPG identity."""
    log.warning('NOTE: in order to re-generate the exact same GPG key later, '
                'run this command with "--time=%d" commandline flag (to set '
                'the timestamp of the GPG key manually).', args.time)
    conn = device.HardwareSigner(user_id=args.user_id,
                                 curve_name=args.ecdsa_curve)
    verifying_key = conn.pubkey(ecdh=False)
    decryption_key = conn.pubkey(ecdh=True)

    if args.subkey:
        primary_bytes = keyring.export_public_key(user_id=args.user_id)
        # subkey for signing
        signing_key = protocol.PublicKey(
            curve_name=args.ecdsa_curve, created=args.time,
            verifying_key=verifying_key, ecdh=False)
        # subkey for encryption
        encryption_key = protocol.PublicKey(
            curve_name=formats.get_ecdh_curve_name(args.ecdsa_curve),
            created=args.time, verifying_key=decryption_key, ecdh=True)
        result = encode.create_subkey(primary_bytes=primary_bytes,
                                      subkey=signing_key,
                                      signer_func=conn.sign)
        result = encode.create_subkey(primary_bytes=result,
                                      subkey=encryption_key,
                                      signer_func=conn.sign)
    else:
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
                                       signer_func=conn.sign)
        result = encode.create_subkey(primary_bytes=result,
                                      subkey=subkey,
                                      signer_func=conn.sign)

    sys.stdout.write(protocol.armor(result, 'PUBLIC KEY BLOCK'))


def run_agent(args):  # pylint: disable=unused-argument
    """Run a simple GPG-agent server."""
    sock_path = keyring.get_agent_sock_path()
    with server.unix_domain_socket_server(sock_path) as sock:
        for conn in agent.yield_connections(sock):
            with contextlib.closing(conn):
                try:
                    agent.handle_connection(conn)
                except Exception as e:  # pylint: disable=broad-except
                    log.exception('gpg-agent failed: %s', e)


def main():
    """Main function."""
    p = argparse.ArgumentParser()
    p.add_argument('-v', '--verbose', default=0, action='count')
    subparsers = p.add_subparsers()
    subparsers.required = True
    subparsers.dest = 'command'

    create_cmd = subparsers.add_parser('create')
    create_cmd.add_argument('user_id')
    create_cmd.add_argument('-s', '--subkey', action='store_true', default=False)
    create_cmd.add_argument('-e', '--ecdsa-curve', default='nist256p1')
    create_cmd.add_argument('-t', '--time', type=int, default=int(time.time()))
    create_cmd.set_defaults(run=run_create)

    agent_cmd = subparsers.add_parser('agent')
    agent_cmd.set_defaults(run=run_agent)

    args = p.parse_args()
    util.setup_logging(verbosity=args.verbose)
    log.warning('This GPG tool is still in EXPERIMENTAL mode, '
                'so please note that the API and features may '
                'change without backwards compatibility!')

    existing_gpg = keyring.gpg_version().decode('ascii')
    required_gpg = '>=2.1.15'
    if semver.match(existing_gpg, required_gpg):
        args.run(args)
    else:
        log.error('Existing gpg2 has version "%s" (%s required)',
                  existing_gpg, required_gpg)


if __name__ == '__main__':
    main()
