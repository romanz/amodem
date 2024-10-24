from numpy.random import RandomState
import numpy as np

from . import utils
from .. import config, dsp, equalizer

config = config.fastest()


def assert_approx(x, y, e=1e-12):
    x = x.flatten()
    y = y.flatten()
    assert dsp.norm(x - y) < e * dsp.norm(x)


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
    y = utils.lfilter(x=x, b=b, a=a)
    y1 = utils.lfilter(x=utils.lfilter(x=x, b=b, a=[1]), b=[1], a=a)
    y2 = utils.lfilter(x=utils.lfilter(x=x, b=[1], a=a), b=b, a=[1])
    assert_approx(y, y1)
    assert_approx(y, y2)

    z = utils.lfilter(x=y, b=a, a=[1])
    z_ = utils.lfilter(x=x, b=b, a=[1])
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
    length = 120
    x = np.sign(RandomState(0).normal(size=length))
    x[-20:] = 0  # make sure the signal has bounded support
    den = np.array([1, -0.6, 0.1])
    num = np.array([0.5])
    y = utils.lfilter(x=x, b=num, a=den)

    lookahead = 2
    h = equalizer.train(
        signal=y, expected=x, order=len(den), lookahead=lookahead)
    assert dsp.norm(h[:lookahead]) < 1e-12

    h = h[lookahead:]
    assert_approx(h, den / num)

    x_ = utils.lfilter(x=y, b=h, a=[1])
    assert_approx(x_, x)
