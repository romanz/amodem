''' Thin wrapper around trezorlib. '''


def client():
    # pylint: disable=import-error
    from trezorlib.client import TrezorClient
    from trezorlib.transport_hid import HidTransport as TrezorHidTransport
    from trezorlib.messages_pb2 import PassphraseAck as TrezorPassphraseAck

    from keepkeylib.client import KeepKeyClient
    from keepkeylib.transport_hid import HidTransport as KeepKeyHidTransport
    from keepkeylib.messages_pb2 import PassphraseAck as KeepKeyPassphraseAck

    devices = list(TrezorHidTransport.enumerate())
    if len(devices) == 1:
        t = TrezorClient(TrezorHidTransport(devices[0]))
        t.callback_PassphraseRequest = lambda msg: TrezorPassphraseAck(passphrase='')
    else:
        devices = list(KeepKeyHidTransport.enumerate())
        if len(devices) != 1:
            msg = '{:d} devices found'.format(len(devices))
            raise IOError(msg)
        t = KeepKeyClient(KeepKeyHidTransport(devices[0]))
        t.callback_PassphraseRequest = lambda msg: KeepKeyPassphraseAck(passphrase='')

    return t


def trezor_identity_type(**kwargs):
    # pylint: disable=import-error
    from trezorlib.types_pb2 import IdentityType
    return IdentityType(**kwargs)

def keepkey_identity_type(**kwargs):
    # pylint: disable=import-error
    from keepkeylib.types_pb2 import IdentityType
    return IdentityType(**kwargs)