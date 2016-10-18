"""GPG-agent utilities."""
import binascii
import contextlib
import logging

from . import decode, device, keyring, protocol
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
    for c in [b'%', b'\n', b'\r']:
        escaped = '%{:02X}'.format(c[0]).encode('ascii')
        data = data.replace(c, escaped)
    return data


def sig_encode(r, s):
    """Serialize ECDSA signature data into GPG S-expression."""
    r = serialize(util.num2bytes(r, 32))
    s = serialize(util.num2bytes(s, 32))
    return b'(7:sig-val(5:ecdsa(1:r32:' + r + b')(1:s32:' + s + b')))'


@contextlib.contextmanager
def open_connection(keygrip_bytes):
    """
    Connect to the device for the specified keygrip.

    Parse GPG public key to find the first user ID, which is used to
    specify the correct signature/decryption key on the device.
    """
    pubkey_dict, user_ids = decode.load_by_keygrip(
        pubkey_bytes=keyring.export_public_keys(),
        keygrip=keygrip_bytes)
    # We assume the first user ID is used to generate TREZOR-based GPG keys.
    user_id = user_ids[0]['value']
    curve_name = protocol.get_curve_name_by_oid(pubkey_dict['curve_oid'])
    ecdh = (pubkey_dict['algo'] == protocol.ECDH_ALGO_ID)

    conn = device.HardwareSigner(user_id, curve_name=curve_name)
    with contextlib.closing(conn):
        pubkey = protocol.PublicKey(
            curve_name=curve_name, created=pubkey_dict['created'],
            verifying_key=conn.pubkey(ecdh=ecdh), ecdh=ecdh)
        assert pubkey.key_id() == pubkey_dict['key_id']
        assert pubkey.keygrip == keygrip_bytes
        yield conn


def pksign(keygrip, digest, algo):
    """Sign a message digest using a private EC key."""
    assert algo == b'8', 'Unsupported hash algorithm ID {}'.format(algo)
    keygrip_bytes = binascii.unhexlify(keygrip)
    with open_connection(keygrip_bytes) as conn:
        r, s = conn.sign(binascii.unhexlify(digest))
        result = sig_encode(r, s)
        log.debug('result: %r', result)
        return result


def _serialize_point(data):
    prefix = '{}:'.format(len(data)).encode('ascii')
    # https://www.gnupg.org/documentation/manuals/assuan/Server-responses.html
    return b'(5:value' + serialize(prefix + data) + b')'


def parse_ecdh(line):
    """Parse ECDH request and return remote public key."""
    prefix, line = line.split(b' ', 1)
    assert prefix == b'D'
    exp, leftover = keyring.parse(keyring.unescape(line))
    log.debug('ECDH s-exp: %r', exp)
    assert not leftover
    label, exp = exp
    assert label == b'enc-val'
    assert exp[0] == b'ecdh'
    items = exp[1:]
    log.debug('ECDH parameters: %r', items)
    return dict(items)[b'e']


def pkdecrypt(keygrip, conn):
    """Handle decryption using ECDH."""
    for msg in [b'S INQUIRE_MAXLEN 4096', b'INQUIRE CIPHERTEXT']:
        keyring.sendline(conn, msg)

    line = keyring.recvline(conn)
    assert keyring.recvline(conn) == b'END'
    remote_pubkey = parse_ecdh(line)

    keygrip_bytes = binascii.unhexlify(keygrip)
    with open_connection(keygrip_bytes) as conn:
        return _serialize_point(conn.ecdh(remote_pubkey))


def handle_connection(conn):
    """Handle connection from GPG binary using the ASSUAN protocol."""
    keygrip = None
    digest = None
    algo = None
    version = keyring.gpg_version()  # "Clone" existing GPG version

    keyring.sendline(conn, b'OK')
    for line in keyring.iterlines(conn):
        parts = line.split(b' ')
        command = parts[0]
        args = parts[1:]
        if command in {b'RESET', b'OPTION', b'HAVEKEY', b'SETKEYDESC'}:
            pass  # reply with OK
        elif command == b'GETINFO':
            keyring.sendline(conn, b'D ' + version)
        elif command == b'AGENT_ID':
            keyring.sendline(conn, b'D TREZOR')  # "Fake" agent ID
        elif command in {b'SIGKEY', b'SETKEY'}:
            keygrip, = args
        elif command == b'SETHASH':
            algo, digest = args
        elif command == b'PKSIGN':
            sig = pksign(keygrip, digest, algo)
            keyring.sendline(conn, b'D ' + sig)
        elif command == b'PKDECRYPT':
            sec = pkdecrypt(keygrip, conn)
            keyring.sendline(conn, b'D ' + sec)
        elif command == b'KEYINFO':
            keygrip, = args
            # Dummy reply (mainly for 'gpg --edit' to succeed).
            # For details, see GnuPG agent KEYINFO command help.
            fmt = 'S KEYINFO {0} X - - - - - - -'
            keyring.sendline(conn, fmt.format(keygrip).encode('ascii'))
        elif command == b'BYE':
            return
        else:
            log.error('unknown request: %r', line)
            return

        keyring.sendline(conn, b'OK')
