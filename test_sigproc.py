import sigproc
import itertools
import config
import numpy as np
import random


def test_qam():
    q = sigproc.QAM(config.symbols)
    r = random.Random(0)
    m = q.bits_per_symbol
    bits = [tuple(r.randint(0, 1) for j in range(m)) for i in range(1024)]
    stream = itertools.chain(*bits)
    S = q.encode(list(stream))
    decoded = list(q.decode(list(S)))
    assert decoded == bits


def test_linreg():
    x = np.array([1, 3, 2, 8, 4, 6, 9, 7, 0, 5])
    a, b = 12.3, 4.56
    y = a * x + b
    a_, b_ = sigproc.linear_regression(x, y)
    assert abs(a - a_) < 1e-10
    assert abs(b - b_) < 1e-10
