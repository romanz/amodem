"""Python wrapper for GnuPG's pinentry."""

import logging
import os
import subprocess

import libagent.gpg.agent

log = logging.getLogger(__name__)


def write(p, line):
    """Send and flush a single line to the subprocess' stdin."""
    log.debug('%s <- %r', p.args, line)
    p.stdin.write(line)
    p.stdin.flush()


def expect(p, prefixes):
    """Read a line and return it without required prefix."""
    resp = p.stdout.readline()
    log.debug('%s -> %r', p.args, resp)
    for prefix in prefixes:
        if resp.startswith(prefix):
            return resp[len(prefix):]
    raise ValueError('Unexpected response: {}'.format(resp))


def interact(title, description, prompt, binary, options):
    """Use GPG pinentry program to interact with the user."""
    p = subprocess.Popen(args=[binary],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         env=os.environ)
    expect(p, [b'OK'])

    title = libagent.gpg.agent.serialize(title.encode('ascii'))
    write(p, b'SETTITLE ' + title + b'\n')
    expect(p, [b'OK'])

    if description:
        description = libagent.gpg.agent.serialize(description.encode('ascii'))
        write(p, b'SETDESC ' + description + b'\n')
        expect(p, [b'OK'])

    if prompt:
        prompt = libagent.gpg.agent.serialize(prompt.encode('ascii'))
        write(p, b'SETPROMPT ' + prompt + b'\n')
        expect(p, [b'OK'])

    log.debug('setting %d options', len(options))
    for opt in options:
        write(p, b'OPTION ' + opt + b'\n')
        expect(p, [b'OK', b'ERR'])

    write(p, b'GETPIN\n')
    pin = expect(p, [b'OK', b'D '])

    p.communicate()  # close stdin and wait for the process to exit
    exit_code = p.wait()
    if exit_code:
        raise subprocess.CalledProcessError(exit_code, binary)

    return pin.decode('ascii').strip()
