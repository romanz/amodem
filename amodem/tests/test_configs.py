from .. import config


def test_bitrates():
    for rate, cfg in sorted(config.bitrates.items()):
        assert rate * 1000 == cfg.modem_bps


def test_slowest():
    c = config.slowest()
    assert c.Npoints == 2
    assert list(c.symbols) == [-1j, 1j]
