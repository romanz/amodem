import binascii
import contextlib
import hashlib
import logging
import os
import select
import subprocess
import threading

import ecdsa

from . import keyring
from .. import server, util

log = logging.getLogger(__name__)


def yield_connections(sock):
    """Run a server on the specified socket."""
    while True:
        log.debug('waiting for connection on %s', sock.getsockname())
        conn, _ = sock.accept()
        conn.settimeout(None)
        log.debug('accepted connection on %s', sock.getsockname())
        yield conn


def serialize(data):
    for c in ['%', '\n', '\r']:
        data = data.replace(c, '%{:02X}'.format(ord(c)))
    return data


def sig_encode(r, s, o):
    r = serialize(util.num2bytes(r, 32))
    s = serialize(util.num2bytes(s, 32))
    return '(7:sig-val(5:ecdsa(1:r32:{})(1:s32:{})))\n'.format(r, s)


def pksign(keygrip, digest):
    pk = 0x99ddae8aee45de830e08889f76ce1f7f993d80a1a05e843ae950b5ba62c16efb
    sk = ecdsa.SigningKey.from_secret_exponent(pk, curve=ecdsa.NIST256p,
                                               hashfunc=hashlib.sha256)
    digest = binascii.unhexlify(digest)
    result = sk.sign_digest_deterministic(digest, hashfunc=hashlib.sha256,
                                          sigencode=sig_encode)
    log.debug('result: %r', result)
    return result


def handle_connection(conn):
    keygrip = None
    digest = None
    algo = None

    conn.sendall('OK\n')
    while True:
        line = keyring.recvline(conn)
        parts = line.split(' ')
        command = parts[0]
        args = parts[1:]
        if command in {'RESET', 'OPTION', 'HAVEKEY', 'SETKEYDESC'}:
            pass  # reply with OK
        elif command == 'GETINFO':
            conn.sendall('D 2.1.11\n')
        elif command == 'AGENT_ID':
            conn.sendall('D TREZOR\n')
        elif command == 'SIGKEY':
            keygrip, = args
        elif command == 'SETHASH':
            algo, digest = args
        elif command == 'PKSIGN':
            sig = pksign(keygrip, digest)
            conn.sendall('D ' + sig)
        else:
            log.error('unknown request: %r', line)
            return

        conn.sendall('OK\n')


def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-10s %(message)s')

    sock_path = os.path.expanduser('~/.gnupg/S.gpg-agent')
    with server.unix_domain_socket_server(sock_path) as sock:
        for conn in yield_connections(sock):
            with contextlib.closing(conn):
                try:
                    handle_connection(conn)
                except EOFError:
                    break


if __name__ == '__main__':
    main()
