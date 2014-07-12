import sampling
import numpy as np


def test_resample():
    x = np.arange(300)
    s = sampling.Sampler(x)
    y = np.array(list(s))

    err = x[1:len(y)+1] - y
    assert np.max(np.abs(err)) < 1e-10


def test_coeffs():
    I = sampling.Interpolator(width=4, resolution=16)
    err = I.filt[0] - [0, 0, 0, 1, 0, 0, 0, 0]
    assert np.max(np.abs(err)) < 1e-10
