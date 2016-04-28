"""Tools for doing signature using gpg-agent."""

import argparse
import binascii
import io
import logging
import os
import re
import socket
import subprocess as sp

from . import decode
from .. import util

log = logging.getLogger(__name__)


def connect(sock_path='~/.gnupg/S.gpg-agent'):
    """Connect to GPG agent's UNIX socket."""
    sock_path = os.path.expanduser(sock_path)
    sp.check_call(['gpg-connect-agent', '/bye'])
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(sock_path)
    return sock


def _communicate(sock, msg):
    sock.sendall(msg + '\n')
    return _recvline(sock)


def _recvline(sock):
    reply = io.BytesIO()

    while True:
        c = sock.recv(1)
        if c == '\n':
            break
        reply.write(c)

    return reply.getvalue()


def _hex(data):
    return binascii.hexlify(data).upper()


def _unescape(s):
    s = bytearray(s)
    i = 0
    while i < len(s):
        if s[i] == ord('%'):
            hex_bytes = s[i+1:i+3]
            value = int(str(hex_bytes), 16)
            s[i:i+3] = [value]
        i += 1
    return bytes(s)


def _parse_term(s):
    size, s = s.split(':', 1)
    size = int(size)
    return s[:size], s[size:]


def _parse(s):
    if s[0] == '(':
        s = s[1:]
        name, s = _parse_term(s)
        values = [name]
        while s[0] != ')':
            value, s = _parse(s)
            values.append(value)
        return values, s[1:]
    else:
        return _parse_term(s)


def sign(sock, keygrip, digest):
    """Sign a digest using specified key using GPG agent."""
    hash_algo = 8  # SHA256
    assert len(digest) == 32

    assert _communicate(sock, 'RESET').startswith('OK')
    assert _communicate(sock, 'SIGKEY {}'.format(keygrip)) == 'OK'
    assert _communicate(sock, 'SETHASH {} {}'.format(hash_algo,
                                                     _hex(digest))) == 'OK'
    assert _communicate(sock, 'PKSIGN') == 'OK'
    line = _recvline(sock).strip()

    line = _unescape(line)
    log.debug('line: %r', line)
    prefix, sig = line.split(' ', 1)
    assert prefix == 'D'

    sig, leftover = _parse(sig)
    assert not leftover

    data, (algo, (r, sig_r), (s, sig_s)) = sig
    assert data == 'sig-val'
    assert algo == 'ecdsa'
    assert r == 'r'
    assert s == 's'
    return (util.bytes2num(sig_r),
            util.bytes2num(sig_s))


def get_keygrip(user_id):
    """Get a keygrip of the primary GPG key of the specified user."""
    args = ['gpg2', '--list-keys', '--with-keygrip', user_id]
    output = sp.check_output(args)
    return re.findall(r'Keygrip = (\w+)', output)[0]


def _main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)-10s %(message)s')

    p = argparse.ArgumentParser()
    p.add_argument('user_id')
    args = p.parse_args()

    p = decode.load_from_gpg(args.user_id)

    digest = os.urandom(32)
    sig = sign(sock=connect(),
               keygrip=get_keygrip(args.user_id),
               digest=digest)
    decode.verify_digest(p, digest, sig, 'gpg-agent signature')


if __name__ == '__main__':
    _main()
