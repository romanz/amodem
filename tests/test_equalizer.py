from amodem import train, dsp, config, send
from numpy.linalg import norm, lstsq
import numpy as np
import itertools


def test_fir():
    a = [1, 0.8, -0.1, 0, 0]
    tx = train.equalizer
    rx = dsp.lfilter(x=tx, b=[1], a=a)
    h_ = dsp.estimate(x=rx, y=tx, order=len(a))
    tx_ = dsp.lfilter(x=rx, b=h_, a=[1])
    assert norm(h_ - a) < 1e-12
    assert (norm(tx - tx_) / norm(tx)) < 1e-12


def test_iir():
    alpha = 0.1
    b = [1, -alpha]
    tx = train.equalizer
    rx = dsp.lfilter(x=tx, b=b, a=[1])
    h_ = dsp.estimate(x=rx, y=tx, order=20)
    tx_ = dsp.lfilter(x=rx, b=h_, a=[1])

    h_expected = np.array([alpha ** i for i in range(len(h_))])
    assert norm(h_ - h_expected) < 1e-12
    assert (norm(tx - tx_) / norm(tx)) < 1e-12

import random

_constellation = [1, 1j, -1, -1j]


def train_symbols(length, seed=0, Nfreq=config.Nfreq):
    r = random.Random(seed)
    choose = lambda: [r.choice(_constellation) for j in range(Nfreq)]
    return np.array([choose() for i in range(length)])


def modulator(length):
    symbols = train_symbols(length)
    carriers = send.sym.carrier
    gain = 1.0 / len(carriers)
    result = []
    for s in symbols:
        result.append(np.dot(s, carriers))
    result = np.concatenate(result).real * gain
    assert np.max(np.abs(result)) <= 1
    return result


def demodulator(signal):
    signal = itertools.chain(signal, itertools.repeat(0))
    return dsp.Demux(signal, config.frequencies)


def test_training():
    L = 1000
    t1 = train_symbols(L)
    t2 = train_symbols(L)
    assert (t1 == t2).all()


def test_commutation():
    x = np.random.RandomState(seed=0).normal(size=1000)
    b = [1, 1j, -1, -1j]
    a = [1, 0.1]
    y = dsp.lfilter(x=x, b=b, a=a)
    y1 = dsp.lfilter(x=dsp.lfilter(x=x, b=b, a=[1]), b=[1], a=a)
    y2 = dsp.lfilter(x=dsp.lfilter(x=x, b=[1], a=a), b=b, a=[1])
    assert norm(y - y1) < 1e-10
    assert norm(y - y2) < 1e-10

    z = dsp.lfilter(x=y, b=a, a=[1])
    z_ = dsp.lfilter(x=x, b=b, a=[1])
    assert norm(z - z_) < 1e-10


def test_modem():
    L = 1000
    sent = train_symbols(L)
    gain = len(send.sym.carrier)
    x = modulator(L) * gain
    s = demodulator(x)
    received = np.array(list(itertools.islice(s, L)))
    err = sent - received
    assert norm(err) < 1e-10


def test_equalizer():
    N = 32
    s = train_symbols(length=100, Nfreq=1).real.squeeze()
    x = [v for v in s for i in range(N)]
    matched = [1.0 / N] * N
    z = dsp.lfilter(x=x, b=matched, a=[1])
    assert norm(z[N-1::N] - s) < 1e-12

    den = np.array([1, 0.125])
    num = np.array([1])
    y = dsp.lfilter(x=x, b=num, a=den)
    y = dsp.lfilter(x=y, b=matched, a=[1])

    A = []
    b = []

    r = 2
    for i in range(len(s)):
        offset = (i+1)*N
        row = y[offset-r:offset]
        A.append(row)
        b.append(s[i])
    A = np.array(A)
    b = np.array(b)
    h, residuals, rank, sv = lstsq(A, b)
    h = h[::-1]
    print(h)

    y1 = dsp.lfilter(x=x, b=num, a=den)
    y2 = dsp.lfilter(x=y1, b=h, a=[1])
    y3 = dsp.lfilter(x=y2, b=matched, a=[1])
    z = y3[N-1::N]
    assert norm(z - s) < 1e-12
