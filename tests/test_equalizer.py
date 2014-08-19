from amodem import train, dsp, config, send
from numpy.linalg import norm
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

def train_symbols(length, seed=0):
    r = random.Random(seed)
    choose = lambda: [r.choice(_constellation) for j in range(config.Nfreq)]
    return np.array([choose() for i in range(length)])

def modulator(length):
    symbols = train_symbols(length)
    carriers = send.sym.carrier
    result = []
    for s in symbols:
        result.append(np.dot(s, carriers) / len(carriers))
    result = np.concatenate(result).real
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

def test_modem():
    L = 1000
    x = modulator(L)
    s = demodulator(x)
    s = list(itertools.islice(s, L))
    sent = train_symbols(L)
    received = np.array(s) * len(send.sym.carrier)
    err = sent - received
    assert norm(err) < 1e-12
