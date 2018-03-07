"""UIs for PIN/passphrase entry."""

import logging
import os
import subprocess

from . import pinentry

log = logging.getLogger(__name__)


def _create_default_options_getter():
    options = []
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


class UI(object):
    """UI for PIN/passphrase entry (for TREZOR devices)."""

    def __init__(self):
        """C-tor."""
        self.options_getter = _create_default_options_getter()
        self.pin_entry_binary = 'pinentry'
        self.passphrase_entry_binary = 'pinentry'

    @classmethod
    def from_config_dict(cls, d):
        """Simple c-tor from configuration dictionary."""
        obj = cls()
        obj.pin_entry_binary = d.get('pin_entry_binary',
                                     obj.pin_entry_binary)
        obj.passphrase_entry_binary = d.get('passphrase_entry_binary',
                                            obj.passphrase_entry_binary)
        return obj

    def get_pin(self):
        """Ask the user for (scrambled) PIN."""
        return pinentry.interact(
            'Use the numeric keypad to describe number positions.\n'
            'The layout is:\n'
            '    7 8 9\n'
            '    4 5 6\n'
            '    1 2 3\n'
            'Please enter PIN:',
            binary=self.pin_entry_binary,
            options=self.options_getter())

    def get_passphrase(self):
        """Ask the user for passphrase."""
        return pinentry.interact(
            'Please enter passphrase:',
            binary=self.passphrase_entry_binary,
            options=self.options_getter())
