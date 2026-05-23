from .. import __main__


def test_version_uses_package_metadata(monkeypatch):
    calls = []

    def version(name):
        calls.append(name)
        return '1.16.0'

    monkeypatch.setattr(__main__, 'metadata_version', version)

    assert __main__._version() == '1.16.0'
    assert calls == ['amodem']
