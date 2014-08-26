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
    t = np.arange(config.Nsym) * config.Ts
    symbol = np.cos(2 * np.pi * config.Fc * t)
    signal = np.concatenate([c * symbol for c in train.prefix])

    sampler = sampling.Sampler(signal)
    freq_err = recv.receive_prefix(sampler, freq=config.Fc)
    assert abs(freq_err) < 1e-16

    try:
        silence = 0 * signal
        recv.receive_prefix(sampling.Sampler(silence), freq=config.Fc)
        assert False
    except ValueError:
        pass
