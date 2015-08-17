''' Thin wrapper around trezorlib. '''


def client():
    # pylint: disable=import-error
    from trezorlib.client import TrezorClient
    from trezorlib.transport_hid import HidTransport
    devices = HidTransport.enumerate()
    if len(devices) != 1:
        msg = '{:d} Trezor devices found'.format(len(devices))
        raise IOError(msg)
    return TrezorClient(HidTransport(devices[0]))


def identity_type(**kwargs):
    # pylint: disable=import-error
    from trezorlib.types_pb2 import IdentityType
    return IdentityType(**kwargs)
