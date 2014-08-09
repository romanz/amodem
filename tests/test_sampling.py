from amodem import sampling
import numpy as np


def test_resample():
    x = np.arange(300)
    s = sampling.Sampler(x, interp=sampling.Interpolator())
    y = s.take(len(x) - s.interp.width - 1)

    err = x[1:len(y)+1] - y
    assert np.max(np.abs(err)) < 1e-10


def test_coeffs():
    I = sampling.Interpolator(width=4, resolution=16)
    err = I.filt[0] - [0, 0, 0, 1, 0, 0, 0, 0]
    assert np.max(np.abs(err)) < 1e-10
