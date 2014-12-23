import numpy as np
import pytest

from amodem import dsp
from amodem import recv
from amodem import train
from amodem import sampling
from amodem import config
config = config.fastest()


def test_detect():
    P = sum(train.prefix)
    t = np.arange(P * config.Nsym) * config.Ts
    x = np.cos(2 * np.pi * config.Fc * t)

    detector = recv.Detector(config)
    samples, amp = detector.run(x)
    assert abs(1 - amp) < 1e-12

    x = np.cos(2 * np.pi * (2*config.Fc) * t)
    with pytest.raises(ValueError):
        detector.run(x)

    with pytest.raises(ValueError):
        detector.max_offset = 0
        detector.run(x)


def test_prefix():
    omega = 2 * np.pi * config.Fc / config.Fs
    symbol = np.cos(omega * np.arange(config.Nsym))
    signal = np.concatenate([c * symbol for c in train.prefix])

    def symbols_stream(signal):
        sampler = sampling.Sampler(signal)
        return dsp.Demux(sampler=sampler, omegas=[omega], Nsym=config.Nsym)
    r = recv.Receiver(config)
    freq_err = r._prefix(symbols_stream(signal))
    assert abs(freq_err) < 1e-16

    with pytest.raises(ValueError):
        silence = 0 * signal
        r._prefix(symbols_stream(silence))


def test_find_start():
    sym = np.cos(2 * np.pi * config.Fc * np.arange(config.Nsym) * config.Ts)
    detector = recv.Detector(config)

    length = 200
    prefix = postfix = np.tile(0 * sym, 50)
    carrier = np.tile(sym, length)
    for offset in range(10):
        prefix = [0] * offset
        bufs = [prefix, prefix, carrier, postfix]
        buf = np.concatenate(bufs)
        start = detector.find_start(buf, length*config.Nsym)
        expected = offset + len(prefix)
        assert expected == start
