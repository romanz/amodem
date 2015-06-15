#!/usr/bin/env python
import socket
import os
import sys
import subprocess
import argparse
import tempfile
import contextlib
import threading
import logging
log = logging.getLogger(__name__)

import protocol
import trezor


def load_keys(key_files):
    keys = []
    for f in key_files:
        k = protocol.load_public_key(f)
        keys.append(k)
    return keys


@contextlib.contextmanager
def unix_domain_socket_server(sock_path):
    log.debug('serving on SSH_AUTH_SOCK=%s', sock_path)
    try:
        os.remove(sock_path)
    except OSError:
        if os.path.exists(sock_path):
            raise

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)
    try:
        yield server
    finally:
        os.remove(sock_path)


def server_thread(server, keys, signer):
    log.debug('server thread started')
    while True:
        log.debug('waiting for connection on %s', server.getsockname())
        try:
            conn, _ = server.accept()
        except socket.error as e:
            log.debug('server error: %s', e, exc_info=True)
            break
        with contextlib.closing(conn):
            protocol.handle_connection(conn, keys, signer)
    log.debug('server thread stopped')


@contextlib.contextmanager
def spawn(func, **kwargs):
    t = threading.Thread(target=func, kwargs=kwargs)
    t.start()
    yield
    t.join()


def run(command, environ):
    log.debug('running %r with %r', command, environ)
    env = dict(os.environ)
    env.update(environ)
    p = subprocess.Popen(args=command, env=env)
    log.debug('subprocess %d is running', p.pid)
    ret = p.wait()
    log.debug('subprocess %d exited: %d', p.pid, ret)
    return ret


def serve(key_files, command, signer, sock_path=None):
    if sock_path is None:
        sock_path = tempfile.mktemp(prefix='ssh-agent-')

    keys = [protocol.parse_public_key(k) for k in key_files]
    environ = {'SSH_AUTH_SOCK': sock_path, 'SSH_AGENT_PID': str(os.getpid())}
    with unix_domain_socket_server(sock_path) as server:
        with spawn(server_thread, server=server, keys=keys, signer=signer):
            try:
                ret = run(command=command, environ=environ)
            finally:
                log.debug('closing server')
                server.shutdown(socket.SHUT_RD)

    log.info('exitcode: %d', ret)
    sys.exit(ret)


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

    client = trezor.Client()

    key_files = []
    for label in args.labels:
        pubkey = client.get_public_key(label=label)
        key_files.append(trezor.export_public_key(pubkey=pubkey, label=label))

    if not args.command:
        sys.stdout.write(''.join(key_files))
        return

    signer = client.sign_ssh_challenge

    try:
        serve(key_files=key_files, command=args.command, signer=signer)
    except KeyboardInterrupt:
        log.info('server stopped')

if __name__ == '__main__':
    main()
