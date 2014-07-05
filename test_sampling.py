import sampling
import numpy as np

def test_resample():
    x = np.arange(300)
    s = sampling.Sampler(x)
    y = np.array(list(s))

    k = s.interp.width - 1
    x = x[k:-k-1]
    err = np.max(np.abs(x - y))
    assert err < 1e-10
