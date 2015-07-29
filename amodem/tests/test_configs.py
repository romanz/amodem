from amodem import config


def test_bitrates():
    for rate, cfg in sorted(config.bitrates.items()):
        assert rate * 1000 == cfg.modem_bps
