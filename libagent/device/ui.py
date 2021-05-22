"""UIs for PIN/passphrase entry."""

import logging
import os
import subprocess
import sys

from .. import util

try:
    from trezorlib.client import PASSPHRASE_ON_DEVICE
except ImportError:
    PASSPHRASE_ON_DEVICE = object()


log = logging.getLogger(__name__)


class UI:
    """UI for PIN/passphrase entry (for TREZOR devices)."""

    def __init__(self, device_type, config=None):
        """C-tor."""
        default_pinentry = 'pinentry'  # by default, use GnuPG pinentry tool
        if config is None:
            config = {}
        self.pin_entry_binary = config.get('pin_entry_binary',
                                           default_pinentry)
        self.passphrase_entry_binary = config.get('passphrase_entry_binary',
                                                  default_pinentry)
        self.options_getter = create_default_options_getter()
        self.device_name = device_type.__name__
        self.cached_passphrase_ack = util.ExpiringCache(
            seconds=float(config.get('cache_expiry_seconds', 'inf')))

    def get_pin(self, _code=None):
        """Ask the user for (scrambled) PIN."""
        description = (
            'Use the numeric keypad to describe number positions.\n'
            'The layout is:\n'
            '    7 8 9\n'
            '    4 5 6\n'
            '    1 2 3')
        return interact(
            title='{} PIN'.format(self.device_name),
            prompt='PIN:',
            description=description,
            binary=self.pin_entry_binary,
            options=self.options_getter())

    def get_passphrase(self, prompt='Passphrase:', available_on_device=False):
        """Ask the user for passphrase."""
        passphrase = None
        if self.cached_passphrase_ack:
            passphrase = self.cached_passphrase_ack.get()
        if passphrase is None:
            env_passphrase = os.environ.get("TREZOR_PASSPHRASE")
            if env_passphrase is not None:
                passphrase = env_passphrase
            elif available_on_device:
                passphrase = PASSPHRASE_ON_DEVICE
            else:
                passphrase = interact(
                    title='{} passphrase'.format(self.device_name),
                    prompt=prompt,
                    description=None,
                    binary=self.passphrase_entry_binary,
                    options=self.options_getter())
        if self.cached_passphrase_ack:
            self.cached_passphrase_ack.set(passphrase)
        return passphrase

    def button_request(self, _code=None):
        """Called by TrezorClient when device interaction is required."""
        # XXX: show notification to the user?


def create_default_options_getter():
    """Return current TTY and DISPLAY settings for GnuPG pinentry."""
    options = []
    if sys.stdin.isatty():  # short-circuit calling `tty`
        try:
            ttyname = subprocess.check_output(args=['tty']).strip()
            options.append(b'ttyname=' + ttyname)
        except subprocess.CalledProcessError as e:
            log.warning('no TTY found: %s', e)

    display = os.environ.get('DISPLAY')
    if display is not None:
        options.append('display={}'.format(display).encode('ascii'))
    else:
        log.warning('DISPLAY not defined')

    log.info('using %s for pinentry options', options)
    return lambda: options


def write(p, line):
    """Send and flush a single line to the subprocess' stdin."""
    log.debug('%s <- %r', p.args, line)
    p.stdin.write(line)
    p.stdin.flush()


class UnexpectedError(Exception):
    """Unexpected response."""


def expect(p, prefixes, confidential=False):
    """Read a line and return it without required prefix."""
    resp = p.stdout.readline()
    log.debug('%s -> %r', p.args, resp if not confidential else '********')
    for prefix in prefixes:
        if resp.startswith(prefix):
            return resp[len(prefix):]
    raise UnexpectedError(resp)


def interact(title, description, prompt, binary, options):
    """Use GPG pinentry program to interact with the user."""
    args = [binary]
    p = subprocess.Popen(args=args,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         env=os.environ)
    p.args = args  # TODO: remove after Python 2 deprecation.
    expect(p, [b'OK'])

    title = util.assuan_serialize(title.encode('ascii'))
    write(p, b'SETTITLE ' + title + b'\n')
    expect(p, [b'OK'])

    if description:
        description = util.assuan_serialize(description.encode('ascii'))
        write(p, b'SETDESC ' + description + b'\n')
        expect(p, [b'OK'])

    if prompt:
        prompt = util.assuan_serialize(prompt.encode('ascii'))
        write(p, b'SETPROMPT ' + prompt + b'\n')
        expect(p, [b'OK'])

    log.debug('setting %d options', len(options))
    for opt in options:
        write(p, b'OPTION ' + opt + b'\n')
        expect(p, [b'OK', b'ERR'])

    write(p, b'GETPIN\n')
    pin = expect(p, [b'OK', b'D '], confidential=True)

    p.communicate()  # close stdin and wait for the process to exit
    exit_code = p.wait()
    if exit_code:
        raise subprocess.CalledProcessError(exit_code, binary)

    return pin.decode('ascii').strip()
