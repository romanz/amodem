from numpy.linalg import norm
import numpy as np

from amodem import train, dsp, config
from amodem import equalizer


def assert_approx(x, y, e=1e-12):
    assert norm(x - y) < e * norm(x)


def test_fir():
    a = [1, 0.8, -0.1, 0, 0]
    tx = train.equalizer
    rx = dsp.lfilter(x=tx, b=[1], a=a)
    h_ = dsp.estimate(x=rx, y=tx, order=len(a))
    tx_ = dsp.lfilter(x=rx, b=h_, a=[1])
    assert_approx(h_, a)
    assert_approx(tx, tx_)


def test_iir():
    alpha = 0.1
    b = [1, -alpha]
    tx = train.equalizer
    rx = dsp.lfilter(x=tx, b=b, a=[1])
    h_ = dsp.estimate(x=rx, y=tx, order=20)
    tx_ = dsp.lfilter(x=rx, b=h_, a=[1])

    h_expected = np.array([alpha ** i for i in range(len(h_))])
    assert_approx(h_, h_expected)
    assert_approx(tx, tx_)


def test_training():
    L = 1000
    t1 = equalizer.train_symbols(L)
    t2 = equalizer.train_symbols(L)
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
    sent = equalizer.train_symbols(L)
    gain = config.Nfreq
    x = equalizer.modulator(sent) * gain
    received = equalizer.demodulator(x, L)
    assert_approx(sent, received)


def test_isi():
    length = 100
    gain = float(config.Nfreq)

    symbols = equalizer.train_symbols(length=length)
    x = equalizer.modulator(symbols)
    assert_approx(equalizer.demodulator(gain * x, size=length), symbols)

    den = np.array([1, -0.6, 0.1])
    num = np.array([0.5])
    y = dsp.lfilter(x=x, b=num, a=den)

    h = equalizer.equalize(y, symbols, order=len(den))
    assert_approx(h, den / num)

    y = dsp.lfilter(x=y, b=h, a=[1])
    z = equalizer.demodulator(gain * y, size=length)
    assert_approx(z, symbols)
