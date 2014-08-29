import numpy as np

from amodem import config
from amodem import recv
from amodem import train
from amodem import sampling


def test_detect():
    P = sum(train.prefix)
    t = np.arange(P * config.Nsym) * config.Ts
    x = np.cos(2 * np.pi * config.Fc * t)
    samples, amp = recv.detect(x, config.Fc)
    assert abs(1 - amp) < 1e-12

    x = np.cos(2 * np.pi * (2*config.Fc) * t)
    try:
        recv.detect(x, config.Fc)
        assert False
    except ValueError:
        pass


def test_prefix():
    symbol = np.cos(2 * np.pi * config.Fc * np.arange(config.Nsym) * config.Ts)
    signal = np.concatenate([c * symbol for c in train.prefix])

    sampler = sampling.Sampler(signal)
    r = recv.Receiver()
    freq_err = r._prefix(sampler, freq=config.Fc)
    assert abs(freq_err) < 1e-16

    try:
        silence = 0 * signal
        r._prefix(sampling.Sampler(silence), freq=config.Fc)
        assert False
    except ValueError:
        pass


def test_find_start():
    sym = np.cos(2 * np.pi * config.Fc * np.arange(config.Nsym) * config.Ts)

    length = 200
    prefix = postfix = np.tile(0 * sym, 50)
    carrier = np.tile(sym, length)
    for offset in range(10):
        prefix = [0] * offset
        bufs = [prefix, prefix, carrier, postfix]
        buf = np.concatenate(bufs)
        start = recv.find_start(buf, length*config.Nsym)
        expected = offset + len(prefix)
        assert expected == start


def test_blocks():
    assert list(recv._blocks([])) == []
