"""GPG-agent utilities."""
import binascii
import contextlib
import logging
import os

from . import decode, encode, keyring
from .. import util

log = logging.getLogger(__name__)


def yield_connections(sock):
    """Run a server on the specified socket."""
    while True:
        log.debug('waiting for connection on %s', sock.getsockname())
        try:
            conn, _ = sock.accept()
        except KeyboardInterrupt:
            return
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
    assert algo == '8', 'Unsupported hash algorithm ID {}'.format(algo)
    user_id = os.environ['TREZOR_GPG_USER_ID']
    pubkey_dict = decode.load_public_key(
        pubkey_bytes=keyring.export_public_key(user_id=user_id),
        use_custom=True, ecdh=False)
    pubkey, conn = encode.load_from_public_key(pubkey_dict=pubkey_dict)
    with contextlib.closing(conn):
        assert pubkey.keygrip == binascii.unhexlify(keygrip)
        r, s = conn.sign(binascii.unhexlify(digest))
        result = sig_encode(r, s)
        log.debug('result: %r', result)
        return result


def _serialize_point(data):
    data = '{}:'.format(len(data)) + data
    # https://www.gnupg.org/documentation/manuals/assuan/Server-responses.html
    for c in ['%', '\n', '\r']:
        data = data.replace(c, '%{:02X}'.format(ord(c)))
    return '(5:value' + data + ')'


def parse_ecdh(line):
    """Parse ECDH request and return remote public key."""
    prefix, line = line.split(' ', 1)
    assert prefix == 'D'
    exp, leftover = keyring.parse(keyring.unescape(line))
    log.debug('ECDH s-exp: %r', exp)
    assert not leftover
    label, exp = exp
    assert label == b'enc-val'
    assert exp[0] == b'ecdh'
    items = exp[1:]
    log.debug('ECDH parameters: %r', items)
    return dict(items)['e']


def pkdecrypt(keygrip, conn):
    """Handle decryption using ECDH."""
    for msg in [b'S INQUIRE_MAXLEN 4096', b'INQUIRE CIPHERTEXT']:
        keyring.sendline(conn, msg)

    line = keyring.recvline(conn)
    assert keyring.recvline(conn) == b'END'
    remote_pubkey = parse_ecdh(line)

    user_id = os.environ['TREZOR_GPG_USER_ID']
    local_pubkey = decode.load_public_key(
        pubkey_bytes=keyring.export_public_key(user_id=user_id),
        use_custom=True, ecdh=True)
    pubkey, conn = encode.load_from_public_key(pubkey_dict=local_pubkey)
    with contextlib.closing(conn):
        assert pubkey.keygrip == binascii.unhexlify(keygrip)
        return _serialize_point(conn.ecdh(remote_pubkey))


def handle_connection(conn):
    """Handle connection from GPG binary using the ASSUAN protocol."""
    keygrip = None
    digest = None
    algo = None
    version = keyring.gpg_version()

    keyring.sendline(conn, b'OK')
    for line in keyring.iterlines(conn):
        parts = line.split(' ')
        command = parts[0]
        args = parts[1:]
        if command in {'RESET', 'OPTION', 'HAVEKEY', 'SETKEYDESC'}:
            pass  # reply with OK
        elif command == 'GETINFO':
            keyring.sendline(conn, b'D ' + version)
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
        elif command == 'KEYINFO':
            keygrip, = args
            # Dummy reply (mainly for 'gpg --edit' to succeed).
            # For details, see GnuPG agent KEYINFO command help.
            fmt = b'S KEYINFO {0} X - - - - - - -'
            keyring.sendline(conn, fmt.format(keygrip))
        elif command == 'BYE':
            return
        else:
            log.error('unknown request: %r', line)
            return

        keyring.sendline(conn, b'OK')
