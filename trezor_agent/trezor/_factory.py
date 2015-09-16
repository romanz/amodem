''' Thin wrapper around trezorlib. '''


def client():
    # pylint: disable=import-error
    from trezorlib.client import TrezorClient
    from trezorlib.transport_hid import HidTransport
    from trezorlib.messages_pb2 import PassphraseAck

    devices = HidTransport.enumerate()
    if len(devices) != 1:
        msg = '{:d} Trezor devices found'.format(len(devices))
        raise IOError(msg)

    t = TrezorClient(HidTransport(devices[0]))
    t.callback_PassphraseRequest = lambda msg: PassphraseAck(passphrase='')
    return t


def identity_type(**kwargs):
    # pylint: disable=import-error
    from trezorlib.types_pb2 import IdentityType
    return IdentityType(**kwargs)
