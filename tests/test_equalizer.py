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

def train_symbols(length, seed=0):
    r = random.Random(seed)
    choose = lambda: [r.choice(_constellation) for j in range(config.Nfreq)]
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

def equalize(signal, carriers, symbols, order):
    ''' symbols[k] = (signal * h) * filters[k] '''
    signal = np.array(signal)
    carriers = np.array(carriers).conj() * (2.0/config.Nsym)
    symbol_stream = []
    for i in range(len(signal) - config.Nsym + 1):
        frame = signal[i:i+config.Nsym]
        symbol_stream.append(np.dot(carriers, frame))
    symbol_stream = np.array(symbol_stream)
    LHS = []
    RHS = []
    offsets = range(0, len(symbol_stream) - order + 1, config.Nsym)
    for j in range(config.Nfreq):
        for i, offset in enumerate(offsets):
            row = list(symbol_stream[offset:offset+order, j])
            LHS.append(row)
            RHS.append(symbols[i, j])

    LHS = np.array(LHS)
    RHS = np.array(RHS)
    return lstsq(LHS, RHS)[0]

def test_modem():
    L = 1000
    sent = train_symbols(L)
    gain = len(send.sym.carrier)
    x = modulator(L) * gain
    h = [0, 1, 0]
    y = dsp.lfilter(x=x, b=h, a=[1])
    h_ = equalize(y, send.sym.carrier, sent, order=len(h))
    assert norm(h - h_) < 1e-10

    s = demodulator(x)
    received = np.array(list(itertools.islice(s, L)))
    err = sent - received
    assert norm(err) < 1e-10
