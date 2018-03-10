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

    def __init__(self, device_type, config):
        """C-tor."""
        default_pinentry = 'pinentry'  # by default, use GnuPG pinentry tool
        self.pin_entry_binary = config.get('pin_entry_binary',
                                           default_pinentry)
        self.passphrase_entry_binary = config.get('passphrase_entry_binary',
                                                  default_pinentry)
        self.options_getter = _create_default_options_getter()
        self.device_name = device_type.__name__

    def get_pin(self):
        """Ask the user for (scrambled) PIN."""
        description = (
            'Use the numeric keypad to describe number positions.\n'
            'The layout is:\n'
            '    7 8 9\n'
            '    4 5 6\n'
            '    1 2 3')
        return pinentry.interact(
            title='{} PIN'.format(self.device_name),
            prompt='PIN:',
            description=description,
            binary=self.pin_entry_binary,
            options=self.options_getter())

    def get_passphrase(self):
        """Ask the user for passphrase."""
        return pinentry.interact(
            title='{} passphrase'.format(self.device_name),
            prompt='Passphrase:',
            description=None,
            binary=self.passphrase_entry_binary,
            options=self.options_getter())
