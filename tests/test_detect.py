import numpy as np
import pytest

from amodem import dsp
from amodem import recv
from amodem import detect
from amodem import equalizer
from amodem import sampling
from amodem import config
from amodem import common
config = config.fastest()


def test_detect():
    P = sum(equalizer.prefix)
    t = np.arange(P * config.Nsym) * config.Ts
    x = np.cos(2 * np.pi * config.Fc * t)

    detector = detect.Detector(config, pylab=common.Dummy())
    samples, amp, freq_err = detector.run(x)
    assert abs(1 - amp) < 1e-12
    assert abs(freq_err) < 1e-12

    x = np.cos(2 * np.pi * (2*config.Fc) * t)
    with pytest.raises(ValueError):
        detector.run(x)

    with pytest.raises(ValueError):
        detector.max_offset = 0
        detector.run(x)


def test_prefix():
    omega = 2 * np.pi * config.Fc / config.Fs
    symbol = np.cos(omega * np.arange(config.Nsym))
    signal = np.concatenate([c * symbol for c in equalizer.prefix])

    def symbols_stream(signal):
        sampler = sampling.Sampler(signal)
        return dsp.Demux(sampler=sampler, omegas=[omega], Nsym=config.Nsym)
    r = recv.Receiver(config, pylab=common.Dummy())
    r._prefix(symbols_stream(signal))

    with pytest.raises(ValueError):
        silence = 0 * signal
        r._prefix(symbols_stream(silence))


def test_find_start():
    sym = np.cos(2 * np.pi * config.Fc * np.arange(config.Nsym) * config.Ts)
    detector = detect.Detector(config, pylab=common.Dummy())

    length = 200
    prefix = postfix = np.tile(0 * sym, 50)
    carrier = np.tile(sym, length)
    for offset in range(32):
        bufs = [prefix, [0] * offset, carrier, postfix]
        buf = np.concatenate(bufs)
        start = detector.find_start(buf)
        expected = offset + len(prefix)
        assert expected == start
