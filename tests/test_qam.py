import random
import itertools

import numpy as np

from amodem import qam
from amodem import config


def test_qam():
    q = qam.QAM(config.symbols)
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
    q = qam.QAM(config.symbols)
    r = np.random.RandomState(seed=0)
    for i in range(10000):
        s = 10*(r.normal() + 1j * r.normal())
        quantize(q, s)
