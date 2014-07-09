import sigproc
import itertools
import common
import numpy as np
import random

def test_qam():
    q = sigproc.QAM(sigproc._symbols)
    r = random.Random(0)
    bits = [tuple(r.randint(0, 1) for j in range(4)) for i in range(1024)]
    stream = itertools.chain(*bits)
    S = q.encode(list(stream))
    decoded = list(q.decode(list(S)))
    assert decoded == bits

def test_drift():
    fc = 10e3
    df = 1.23
    f = fc + df
    x = np.cos(2 * np.pi * f / common.Fs * np.arange(common.Fs))
    S = sigproc.extract_symbols(x, fc)
    S = np.array(list(S))
    df_ = sigproc.drift(S) / common.Tsym
    assert abs(df - df_) < 1e-5, (df, df_)
