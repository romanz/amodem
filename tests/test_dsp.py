from amodem import dsp
from amodem import sampling
from amodem import config
import utils

import numpy as np
import random
import itertools

config = config.fastest()


def test_linreg():
    x = np.array([1, 3, 2, 8, 4, 6, 9, 7, 0, 5])
    a, b = 12.3, 4.56
    y = a * x + b
    a_, b_ = dsp.linear_regression(x, y)
    assert abs(a - a_) < 1e-10
    assert abs(b - b_) < 1e-10


def test_filter():
    x = range(10)
    y = utils.lfilter(b=[1], a=[1], x=x)
    assert (np.array(x) == y).all()

    x = [1] + [0] * 10
    y = utils.lfilter(b=[0.5], a=[1, -0.5], x=x)
    assert list(y) == [0.5 ** (i+1) for i in range(len(x))]


def test_demux():
    freqs = np.array([1e3, 2e3])
    omegas = 2 * np.pi * freqs / config.Fs
    carriers = [dsp.exp_iwt(2*np.pi*f/config.Fs, config.Nsym) for f in freqs]
    syms = [3, 2j]
    sig = np.dot(syms, carriers)
    res = dsp.Demux(sampling.Sampler(sig.real), omegas, config.Nsym)
    res = np.array(list(res))
    assert np.max(np.abs(res - syms)) < 1e-12


def test_qam():
    q = dsp.MODEM(config.symbols)
    r = random.Random(0)
    m = q.bits_per_symbol
    bits = [tuple(r.randint(0, 1) for j in range(m)) for i in range(1024)]
    stream = itertools.chain(*bits)
    S = list(q.encode(list(stream)))
    decoded = list(q.decode(S))
    assert decoded == bits

    def noise(A):
        return A*(r.uniform(-1, 1) + 1j*r.uniform(-1, 1))

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
    q = dsp.MODEM(config.symbols)
    r = np.random.RandomState(seed=0)
    for i in range(10000):
        s = 10*(r.normal() + 1j * r.normal())
        quantize(q, s)


def test_prbs():
    r = list(itertools.islice(dsp.prbs(reg=1, poly=0x7, bits=2), 4))
    assert r == [1, 2, 3, 1]

    r = list(itertools.islice(dsp.prbs(reg=1, poly=0x7, bits=1), 4))
    assert r == [1, 0, 1, 1]

    r = list(itertools.islice(dsp.prbs(reg=1, poly=0xd, bits=3), 8))
    assert r == [1, 2, 4, 5, 7, 3, 6, 1]

    r = list(itertools.islice(dsp.prbs(reg=1, poly=0xd, bits=2), 8))
    assert r == [1, 2, 0, 1, 3, 3, 2, 1]

    period = 2 ** 16 - 1
    r = list(itertools.islice(dsp.prbs(reg=1, poly=0x1100b, bits=16), period))
    r.sort()
    assert r == list(range(1, 2 ** 16))
