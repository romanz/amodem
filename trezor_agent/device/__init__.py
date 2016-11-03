"""Cryptographic hardware device management."""

import logging

from . import trezor
from . import keepkey
from . import ledger
from . import interface

log = logging.getLogger(__name__)

DEVICE_TYPES = [
    trezor.Trezor,
    keepkey.KeepKey,
    ledger.LedgerNanoS,
]


def detect():
    """Detect the first available device and return it to the user."""
    for device_type in DEVICE_TYPES:
        try:
            with device_type() as d:
                return d
        except interface.NotFoundError as e:
            log.debug('device not found: %s', e)
    raise IOError('No device found!')
