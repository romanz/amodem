import mock
import pytest

from .. import factory


def test_load():

    def single():
        return [0]

    def nothing():
        return []

    def double():
        return [1, 2]

    assert factory.load(loaders=[single]) == 0
    assert factory.load(loaders=[single, nothing]) == 0
    assert factory.load(loaders=[nothing, single]) == 0

    with pytest.raises(IOError):
        factory.load(loaders=[])

    with pytest.raises(IOError):
        factory.load(loaders=[single, single])

    with pytest.raises(IOError):
        factory.load(loaders=[double])


def factory_load_client(**kwargs):
    # pylint: disable=protected-access
    return list(factory._load_client(**kwargs))


def test_load_nothing():
    hid_transport = mock.Mock(spec_set=['enumerate'])
    hid_transport.enumerate.return_value = []
    result = factory_load_client(
        name=None,
        client_type=None,
        hid_transport=hid_transport,
        passphrase_ack=None,
        identity_type=None,
        required_version=None,
        call_exception=None)
    assert result == []


def create_client_type(version):
    conn = mock.Mock(spec=[])
    conn.features = mock.Mock(spec=[])
    major, minor, patch = version.split('.')
    conn.features.device_id = 'DEVICE_ID'
    conn.features.label = 'LABEL'
    conn.features.vendor = 'VENDOR'
    conn.features.major_version = major
    conn.features.minor_version = minor
    conn.features.patch_version = patch
    conn.features.revision = b'\x12\x34\x56\x78'
    return mock.Mock(spec_set=[], return_value=conn)


def test_load_single():
    hid_transport = mock.Mock(spec_set=['enumerate'])
    hid_transport.enumerate.return_value = [0]
    for version in ('1.3.4', '1.3.5', '1.4.0', '2.0.0'):
        passphrase_ack = mock.Mock(spec_set=[])
        client_type = create_client_type(version)
        client_wrapper, = factory_load_client(
            name='DEVICE_NAME',
            client_type=client_type,
            hid_transport=hid_transport,
            passphrase_ack=passphrase_ack,
            identity_type=None,
            required_version='>=1.3.4',
            call_exception=None)
        assert client_wrapper.connection is client_type.return_value
        assert client_wrapper.device_name == 'DEVICE_NAME'
        client_wrapper.connection.callback_PassphraseRequest('MESSAGE')
        assert passphrase_ack.mock_calls == [mock.call(passphrase='')]


def test_load_old():
    hid_transport = mock.Mock(spec_set=['enumerate'])
    hid_transport.enumerate.return_value = [0]
    for version in ('1.3.3', '1.2.5', '1.1.0', '0.9.9'):
        with pytest.raises(ValueError):
            factory_load_client(
                name='DEVICE_NAME',
                client_type=create_client_type(version),
                hid_transport=hid_transport,
                passphrase_ack=None,
                identity_type=None,
                required_version='>=1.3.4',
                call_exception=None)
