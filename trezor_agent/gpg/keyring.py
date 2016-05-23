"""Tools for doing signature using gpg-agent."""

import binascii
import io
import logging
import os
import re
import socket
import subprocess

from . import decode
from .. import util

log = logging.getLogger(__name__)


def connect_to_agent(sock_path='~/.gnupg/S.gpg-agent'):
    """Connect to GPG agent's UNIX socket."""
    sock_path = os.path.expanduser(sock_path)
    subprocess.check_call(['gpg-connect-agent', '/bye'])
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(sock_path)
    return sock


def _communicate(sock, msg):
    msg += '\n'
    sock.sendall(msg.encode('ascii'))
    log.debug('-> %r', msg)
    return _recvline(sock)


def _recvline(sock):
    reply = io.BytesIO()

    while True:
        c = sock.recv(1)
        if c == b'\n':
            break
        reply.write(c)

    result = reply.getvalue()
    log.debug('<- %r', result)
    return result


def _hex(data):
    return binascii.hexlify(data).upper().decode('ascii')


def _unescape(s):
    s = bytearray(s)
    i = 0
    while i < len(s):
        if s[i] == ord('%'):
            hex_bytes = bytes(s[i+1:i+3])
            value = int(hex_bytes.decode('ascii'), 16)
            s[i:i+3] = [value]
        i += 1
    return bytes(s)


def _parse_term(s):
    size, s = s.split(b':', 1)
    size = int(size)
    return s[:size], s[size:]


def _parse(s):
    if s.startswith(b'('):
        s = s[1:]
        name, s = _parse_term(s)
        values = [name]
        while not s.startswith(b')'):
            value, s = _parse(s)
            values.append(value)
        return values, s[1:]
    else:
        return _parse_term(s)


def _parse_ecdsa_sig(args):
    (r, sig_r), (s, sig_s) = args
    assert r == b'r'
    assert s == b's'
    return (util.bytes2num(sig_r),
            util.bytes2num(sig_s))

_parse_dsa_sig = _parse_ecdsa_sig


def _parse_rsa_sig(args):
    (s, sig_s), = args
    assert s == b's'
    return (util.bytes2num(sig_s),)


def _parse_sig(sig):
    label, sig = sig
    assert label == b'sig-val'
    algo_name = sig[0]
    parser = {b'rsa': _parse_rsa_sig,
              b'ecdsa': _parse_ecdsa_sig,
              b'dsa': _parse_dsa_sig}[algo_name]
    return parser(args=sig[1:])


def sign_digest(sock, keygrip, digest):
    """Sign a digest using specified key using GPG agent."""
    hash_algo = 8  # SHA256
    assert len(digest) == 32

    assert _communicate(sock, 'RESET').startswith(b'OK')

    ttyname = subprocess.check_output('tty').strip()
    options = ['ttyname={}'.format(ttyname)]  # set TTY for passphrase entry
    for opt in options:
        assert _communicate(sock, 'OPTION {}'.format(opt)) == b'OK'

    assert _communicate(sock, 'SIGKEY {}'.format(keygrip)) == b'OK'
    assert _communicate(sock, 'SETHASH {} {}'.format(hash_algo,
                                                     _hex(digest))) == b'OK'

    desc = ('Please+enter+the+passphrase+to+unlock+the+OpenPGP%0A'
            'secret+key,+to+sign+a+new+TREZOR-based+subkey')
    assert _communicate(sock, 'SETKEYDESC {}'.format(desc)) == b'OK'
    assert _communicate(sock, 'PKSIGN') == b'OK'
    line = _recvline(sock).strip()
    line = _unescape(line)
    log.debug('unescaped: %r', line)
    prefix, sig = line.split(b' ', 1)
    if prefix != b'D':
        raise ValueError(prefix)

    sig, leftover = _parse(sig)
    assert not leftover, leftover
    return _parse_sig(sig)


def get_keygrip(user_id):
    """Get a keygrip of the primary GPG key of the specified user."""
    args = ['gpg2', '--list-keys', '--with-keygrip', user_id]
    output = subprocess.check_output(args).decode('ascii')
    return re.findall(r'Keygrip = (\w+)', output)[0]


def get_public_key(user_id, use_custom=False):
    """Load existing GPG public key for `user_id` from local keyring."""
    args = ['gpg2', '--export'] + ([user_id] if user_id else [])
    pubkey_bytes = subprocess.check_output(args=args)
    if pubkey_bytes:
        return decode.load_public_key(io.BytesIO(pubkey_bytes),
                                      use_custom=use_custom)
    else:
        log.error('could not find public key %r in local GPG keyring', user_id)
        raise KeyError(user_id)
