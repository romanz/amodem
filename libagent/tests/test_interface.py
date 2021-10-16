from ..device import interface


def test_unicode():
    i = interface.Identity('ko\u017eu\u0161\u010dek@host', 'ed25519')
    assert i.to_bytes() == b'kozuscek@host'
    assert sorted(i.items()) == [('host', 'host'), ('user', 'kozuscek')]
