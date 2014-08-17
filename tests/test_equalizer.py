from amodem import train
from amodem import dsp
from numpy.linalg import norm
import numpy as np


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
