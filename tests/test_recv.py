from amodem import config, recv, train
import numpy as np

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
    symbols = [[i] for i in train.prefix]
    freq_err, phase_err = recv.receive_prefix(symbols)
    assert freq_err == 0
    assert phase_err == 0

    try:
        recv.receive_prefix([[0]] * len(train.prefix))
        assert False
    except ValueError:
        pass
