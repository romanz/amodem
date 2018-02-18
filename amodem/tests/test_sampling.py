from amodem import sampling
from amodem import common

import numpy as np
from io import BytesIO


def test_resample():
    x = np.sin(2*np.pi * 10 * np.linspace(0, 1, 1001))
    src = BytesIO(common.dumps(x))
    dst = BytesIO()
    sampling.resample(src=src, dst=dst, df=0.0)
    y = common.loads(dst.getvalue())
    err = x[:len(y)] - y
    assert np.max(np.abs(err)) < 1e-4

    dst = BytesIO()
    sampling.resample(src=BytesIO(b'\x00\x00'), dst=dst, df=0.0)
    assert dst.tell() == 0


def test_coeffs():
    interp = sampling.Interpolator(width=4, resolution=16)
    err = interp.filt[0] - [0, 0, 0, 1, 0, 0, 0, 0]
    assert np.max(np.abs(err)) < 1e-10
