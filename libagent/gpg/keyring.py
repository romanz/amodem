"""Tools for doing signature using gpg-agent."""
from __future__ import absolute_import, print_function, unicode_literals

import binascii
import io
import logging
import os
import re
import socket
import subprocess

from .. import util

log = logging.getLogger(__name__)


def check_output(args, env=None, sp=subprocess):
    """Call an external binary and return its stdout."""
    log.debug('calling %s with env %s', args, env)
    output = sp.check_output(args=args, env=env)
    log.debug('output: %r', output)
    return output


def get_agent_sock_path(env=None, sp=subprocess):
    """Parse gpgconf output to find out GPG agent UNIX socket path."""
    args = [util.which('gpgconf'), '--list-dirs']
    output = check_output(args=args, env=env, sp=sp)
    lines = output.strip().split(b'\n')
    dirs = dict(line.split(b':', 1) for line in lines)
    log.debug('%s: %s', args, dirs)
    return dirs[b'agent-socket']


def connect_to_agent(env=None, sp=subprocess):
    """Connect to GPG agent's UNIX socket."""
    sock_path = get_agent_sock_path(sp=sp, env=env)
    # Make sure the original gpg-agent is running.
    check_output(args=['gpg-connect-agent', '/bye'], sp=sp)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(sock_path)
    return sock


def communicate(sock, msg):
    """Send a message and receive a single line."""
    sendline(sock, msg.encode('ascii'))
    return recvline(sock)


def sendline(sock, msg, confidential=False):
    """Send a binary message, followed by EOL."""
    log.debug('<- %r', ('<snip>' if confidential else msg))
    sock.sendall(msg + b'\n')


def recvline(sock):
    """Receive a single line from the socket."""
    reply = io.BytesIO()

    while True:
        c = sock.recv(1)
        if not c:
            return None  # socket is closed

        if c == b'\n':
            break
        reply.write(c)

    result = reply.getvalue()
    log.debug('-> %r', result)
    return result


def iterlines(conn):
    """Iterate over input, split by lines."""
    while True:
        line = recvline(conn)
        if line is None:
            break
        yield line


def unescape(s):
    """Unescape ASSUAN message (0xAB <-> '%AB')."""
    s = bytearray(s)
    i = 0
    while i < len(s):
        if s[i] == ord('%'):
            hex_bytes = bytes(s[i+1:i+3])
            value = int(hex_bytes.decode('ascii'), 16)
            s[i:i+3] = [value]
        i += 1
    return bytes(s)


def parse_term(s):
    """Parse single s-expr term from bytes."""
    size, s = s.split(b':', 1)
    size = int(size)
    return s[:size], s[size:]


def parse(s):
    """Parse full s-expr from bytes."""
    if s.startswith(b'('):
        s = s[1:]
        name, s = parse_term(s)
        values = [name]
        while not s.startswith(b')'):
            value, s = parse(s)
            values.append(value)
        return values, s[1:]

    return parse_term(s)


def _parse_ecdsa_sig(args):
    (r, sig_r), (s, sig_s) = args
    assert r == b'r'
    assert s == b's'
    return (util.bytes2num(sig_r),
            util.bytes2num(sig_s))


# DSA and EDDSA happen to have the same structure as ECDSA signatures
_parse_dsa_sig = _parse_ecdsa_sig
_parse_eddsa_sig = _parse_ecdsa_sig


def _parse_rsa_sig(args):
    (s, sig_s), = args
    assert s == b's'
    return (util.bytes2num(sig_s),)


def parse_sig(sig):
    """Parse signature integer values from s-expr."""
    label, sig = sig
    assert label == b'sig-val'
    algo_name = sig[0]
    parser = {b'rsa': _parse_rsa_sig,
              b'ecdsa': _parse_ecdsa_sig,
              b'eddsa': _parse_eddsa_sig,
              b'dsa': _parse_dsa_sig}[algo_name]
    return parser(args=sig[1:])


def sign_digest(sock, keygrip, digest, sp=subprocess, environ=None):
    """Sign a digest using specified key using GPG agent."""
    hash_algo = 8  # SHA256
    assert len(digest) == 32

    assert communicate(sock, 'RESET').startswith(b'OK')

    ttyname = check_output(args=['tty'], sp=sp).strip()
    options = ['ttyname={}'.format(ttyname)]  # set TTY for passphrase entry

    display = (environ or os.environ).get('DISPLAY')
    if display is not None:
        options.append('display={}'.format(display))

    for opt in options:
        assert communicate(sock, 'OPTION {}'.format(opt)) == b'OK'

    assert communicate(sock, 'SIGKEY {}'.format(keygrip)) == b'OK'
    hex_digest = binascii.hexlify(digest).upper().decode('ascii')
    assert communicate(sock, 'SETHASH {} {}'.format(hash_algo,
                                                    hex_digest)) == b'OK'

    assert communicate(sock, 'SETKEYDESC '
                       'Sign+a+new+TREZOR-based+subkey') == b'OK'
    assert communicate(sock, 'PKSIGN') == b'OK'
    while True:
        line = recvline(sock).strip()
        if line.startswith(b'S PROGRESS'):
            continue
        else:
            break
    line = unescape(line)
    log.debug('unescaped: %r', line)
    prefix, sig = line.split(b' ', 1)
    if prefix != b'D':
        raise ValueError(prefix)

    sig, leftover = parse(sig)
    assert not leftover, leftover
    return parse_sig(sig)


def get_gnupg_components(sp=subprocess):
    """Parse GnuPG components' paths."""
    args = [util.which('gpgconf'), '--list-components']
    output = check_output(args=args, sp=sp)
    components = dict(re.findall('(.*):.*:(.*)', output.decode('utf-8')))
    log.debug('gpgconf --list-components: %s', components)
    return components


@util.memoize
def get_gnupg_binary(sp=subprocess, neopg_binary=None):
    """Starting GnuPG 2.2.x, the default installation uses `gpg`."""
    if neopg_binary:
        return neopg_binary
    return get_gnupg_components(sp=sp)['gpg']


def gpg_command(args, env=None):
    """Prepare common GPG command line arguments."""
    if env is None:
        env = os.environ
    cmd = get_gnupg_binary(neopg_binary=env.get('NEOPG_BINARY'))
    return [cmd] + args


def get_keygrip(user_id, sp=subprocess):
    """Get a keygrip of the primary GPG key of the specified user."""
    args = gpg_command(['--list-keys', '--with-keygrip', user_id])
    output = check_output(args=args, sp=sp).decode('utf-8')
    return re.findall(r'Keygrip = (\w+)', output)[0]


def gpg_version(sp=subprocess):
    """Get a keygrip of the primary GPG key of the specified user."""
    args = gpg_command(['--version'])
    output = check_output(args=args, sp=sp)
    line = output.split(b'\n')[0]  # b'gpg (GnuPG) 2.1.11'
    line = line.split(b' ')[-1]  # b'2.1.11'
    line = line.split(b'-')[0]  # remove trailing version parts
    return line.split(b'v')[-1]  # remove 'v' prefix


def export_public_key(user_id, env=None, sp=subprocess):
    """Export GPG public key for specified `user_id`."""
    args = gpg_command(['--export', user_id])
    result = check_output(args=args, env=env, sp=sp)
    if not result:
        log.error('could not find public key %r in local GPG keyring', user_id)
        raise KeyError(user_id)
    return result


def export_public_keys(env=None, sp=subprocess):
    """Export all GPG public keys."""
    args = gpg_command(['--export'])
    result = check_output(args=args, env=env, sp=sp)
    if not result:
        raise KeyError('No GPG public keys found at env: {!r}'.format(env))
    return result


def create_agent_signer(user_id):
    """Sign digest with existing GPG keys using gpg-agent tool."""
    sock = connect_to_agent(env=os.environ)
    keygrip = get_keygrip(user_id)

    def sign(digest):
        """Sign the digest and return an ECDSA/RSA/DSA signature."""
        return sign_digest(sock=sock, keygrip=keygrip, digest=digest)

    return sign
