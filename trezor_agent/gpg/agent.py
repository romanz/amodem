"""GPG-agent utilities."""
import binascii
import contextlib
import logging
import os

from . import decode, encode, keyring
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
    """Serialize data according to ASSUAN protocol."""
    for c in ['%', '\n', '\r']:
        data = data.replace(c, '%{:02X}'.format(ord(c)))
    return data


def sig_encode(r, s):
    """Serialize ECDSA signature data into GPG S-expression."""
    r = serialize(util.num2bytes(r, 32))
    s = serialize(util.num2bytes(s, 32))
    return '(7:sig-val(5:ecdsa(1:r32:{})(1:s32:{})))'.format(r, s)


def pksign(keygrip, digest, algo):
    """Sign a message digest using a private EC key."""
    assert algo == '8'
    pubkey = decode.load_public_key(keyring.export_public_key(user_id=None),
                                    use_custom=True)
    f = encode.Factory.from_public_key(pubkey=pubkey,
                                       user_id=pubkey['user_id'])
    with contextlib.closing(f):
        assert f.pubkey.keygrip == binascii.unhexlify(keygrip)
        r, s = f.conn.sign(binascii.unhexlify(digest))
        result = sig_encode(r, s)
        log.debug('result: %r', result)
        return result


def _serialize_point(data):
    data = '{}:'.format(len(data)) + data
    # https://www.gnupg.org/documentation/manuals/assuan/Server-responses.html
    for c in ['%', '\n', '\r']:
        data = data.replace(c, '%{:02X}'.format(ord(c)))
    return '(5:value' + data + ')'


def pkdecrypt(keygrip, conn):
    for msg in [b'S INQUIRE_MAXLEN 4096', b'INQUIRE CIPHERTEXT']:
        keyring.sendline(conn, msg)

    line = keyring.recvline(conn)
    prefix, line = line.split(' ', 1)
    assert prefix == 'D'
    exp, leftover = keyring.parse(keyring.unescape(line))

    pubkey = decode.load_public_key(keyring.export_public_key(user_id=None),
                                    use_custom=True)
    f = encode.Factory.from_public_key(pubkey=pubkey,
                                       user_id=pubkey['user_id'])
    with contextlib.closing(f):
        ### assert f.pubkey.keygrip == binascii.unhexlify(keygrip)
        pubkey = dict(exp[1][1:])['e']
        shared_secret = f.get_shared_secret(pubkey)

    assert len(shared_secret) == 65
    assert shared_secret[:1] == b'\x04'
    return _serialize_point(shared_secret)


def iterlines(conn):
    """Iterate over input, split by lines."""
    while True:
        line = keyring.recvline(conn)
        if line is None:
            break
        yield line


def handle_connection(conn):
    """Handle connection from GPG binary using the ASSUAN protocol."""
    keygrip = None
    digest = None
    algo = None

    keyring.sendline(conn, b'OK')
    for line in iterlines(conn):
        parts = line.split(' ')
        command = parts[0]
        args = parts[1:]
        if command in {'RESET', 'OPTION', 'HAVEKEY', 'SETKEYDESC'}:
            pass  # reply with OK
        elif command == 'GETINFO':
            keyring.sendline(conn, b'D 2.1.11')
        elif command == 'AGENT_ID':
            keyring.sendline(conn, b'D TREZOR')
        elif command in {'SIGKEY', 'SETKEY'}:
            keygrip, = args
        elif command == 'SETHASH':
            algo, digest = args
        elif command == 'PKSIGN':
            sig = pksign(keygrip, digest, algo)
            keyring.sendline(conn, b'D ' + sig)
        elif command == 'PKDECRYPT':
            sec = pkdecrypt(keygrip, conn)
            keyring.sendline(conn, b'D ' + sec)
        elif command == 'END':
            log.error('closing connection')
            return
        else:
            log.error('unknown request: %r', line)
            return

        keyring.sendline(conn, b'OK')


def main():
    """Run a simple GPG-agent server."""
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')

    sock_path = os.path.expanduser('~/.gnupg/S.gpg-agent')
    with server.unix_domain_socket_server(sock_path) as sock:
        for conn in yield_connections(sock):
            with contextlib.closing(conn):
                handle_connection(conn)


if __name__ == '__main__':
    main()
