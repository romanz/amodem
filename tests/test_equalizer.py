from numpy.linalg import norm
from numpy.random import RandomState
import numpy as np

from amodem import dsp
from amodem import equalizer
from amodem import config
config = config.fastest()


def assert_approx(x, y, e=1e-12):
    assert norm(x - y) < e * norm(x)


def test_training():
    L = 1000
    e = equalizer.Equalizer(config)
    t1 = e.train_symbols(L)
    t2 = e.train_symbols(L)
    assert (t1 == t2).all()


def test_commutation():
    x = np.random.RandomState(seed=0).normal(size=1000)
    b = [1, 1j, -1, -1j]
    a = [1, 0.1]
    y = dsp.lfilter(x=x, b=b, a=a)
    y1 = dsp.lfilter(x=dsp.lfilter(x=x, b=b, a=[1]), b=[1], a=a)
    y2 = dsp.lfilter(x=dsp.lfilter(x=x, b=[1], a=a), b=b, a=[1])
    assert_approx(y, y1)
    assert_approx(y, y2)

    z = dsp.lfilter(x=y, b=a, a=[1])
    z_ = dsp.lfilter(x=x, b=b, a=[1])
    assert_approx(z, z_)


def test_modem():
    L = 1000
    e = equalizer.Equalizer(config)
    sent = e.train_symbols(L)
    gain = config.Nfreq
    x = e.modulator(sent) * gain
    received = e.demodulator(x, L)
    assert_approx(sent, received)


def test_signal():
    length = 100
    x = np.sign(RandomState(0).normal(size=length))
    den = np.array([1, -0.6, 0.1])
    num = np.array([0.5])
    y = dsp.lfilter(x=x, b=num, a=den)
    e = equalizer.Equalizer(config)

    lookahead = 2
    h = e.equalize_signal(
        signal=y, expected=x, order=len(den), lookahead=lookahead)
    assert norm(h[:lookahead]) < 1e-12

    h = h[lookahead:]
    assert_approx(h, den / num)

    x_ = dsp.lfilter(x=y, b=h, a=[1])
    assert_approx(x_, x)
