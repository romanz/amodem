import random
import itertools
import numpy as np
from numpy.linalg import norm

from amodem import dsp
from amodem import config


def test_qam():
    q = dsp.QAM(config.symbols)
    r = random.Random(0)
    m = q.bits_per_symbol
    bits = [tuple(r.randint(0, 1) for j in range(m)) for i in range(1024)]
    stream = itertools.chain(*bits)
    S = list(q.encode(list(stream)))
    decoded = list(q.decode(S))
    assert decoded == bits

    noise = lambda A: A*(r.uniform(-1, 1) + 1j*r.uniform(-1, 1))
    noised_symbols = [(s + noise(1e-3)) for s in S]
    decoded = list(q.decode(noised_symbols))
    assert decoded == bits


def quantize(q, s):
    bits, = list(q.decode([s]))
    r, = q.encode(bits)
    index = np.argmin(np.abs(s - q.symbols))
    expected = q.symbols[index]
    assert r == expected


def test_overflow():
    q = dsp.QAM(config.symbols)
    r = np.random.RandomState(seed=0)
    for i in range(10000):
        s = 10*(r.normal() + 1j * r.normal())
        quantize(q, s)


def test_linreg():
    x = np.array([1, 3, 2, 8, 4, 6, 9, 7, 0, 5])
    a, b = 12.3, 4.56
    y = a * x + b
    a_, b_ = dsp.linear_regression(x, y)
    assert abs(a - a_) < 1e-10
    assert abs(b - b_) < 1e-10


def test_filter():
    x = range(10)
    y = dsp.lfilter(b=[1], a=[1], x=x)
    assert (np.array(x) == y).all()

    x = [1] + [0] * 10
    y = dsp.lfilter(b=[0.5], a=[1, -0.5], x=x)
    assert list(y) == [0.5 ** (i+1) for i in range(len(x))]


def test_estimate():
    r = np.random.RandomState(seed=0)
    x = r.uniform(-1, 1, [1000])
    x[:10] = 0
    x[len(x)-10:] = 0

    c = 1.23
    y = c * x
    c_, = dsp.estimate(x=x, y=y, order=1)
    assert abs(c - c_) < 1e-12

    h = [1, 1]
    y = dsp.lfilter(b=h, a=[1], x=x)
    h_ = dsp.estimate(x=x, y=y, order=len(h))
    assert norm(h - h_) < 1e-12

    h = [0.1, 0.6, 0.9, 0.7, -0.2]
    L = len(h) // 2

    y = dsp.lfilter(b=h, a=[1], x=x)
    h_ = dsp.estimate(
        x=x[:len(x)-L], y=y[L:],
        order=len(h), lookahead=L
    )
    assert norm(h - h_) < 1e-12

    y_ = dsp.lfilter(b=h_, a=[1], x=x)
    assert norm(y - y_) < 1e-12


def test_demux():
    freqs = [1e3, 2e3]
    carriers = [dsp.exp_iwt(f, config.Nsym) for f in freqs]
    syms = [3, 2j]
    sig = np.dot(syms, carriers)
    res = dsp.Demux(sig.real, freqs)
    res = np.array(list(res))
    assert np.max(np.abs(res - syms)) < 1e-12
