import common
import numpy as np

def iterlist(x, *args, **kwargs):
    x = np.array(x)
    return [(offset, list(buf)) for offset, buf in common.iterate(x, *args, **kwargs)]

def test_iterate():
    N = 10
    assert iterlist(range(N), 1) == [(i, [i]) for i in range(N)]
    assert iterlist(range(N), 1) == [(i, [i]) for i in range(N)]
    assert iterlist(range(N), 2) == [(i, [i, i+1]) for i in range(N-1)]
    assert iterlist(range(N), 3) == [(i, [i, i+1, i+2]) for i in range(N-2)]
    assert iterlist(range(N), 3, advance=2) == [(i, [i, i+1, i+2]) for i in range(0, N-2, 2)]
    assert iterlist(range(N), 3, advance=3) == [(i, [i, i+1, i+2]) for i in range(0, N-2, 3)]
    assert iterlist(range(N), 2, offset=5) == [(i, [i, i+1]) for i in range(5, N-1)]
    assert iterlist(range(N), 1, func=lambda b: -b) == [(i, [-i]) for i in range(N)]

def test_split():
    L = [(i*2, i*2+1) for i in range(10)]
    iters = common.split(L, n=2)
    assert zip(*iters) == L

    for i in [0, 1]:
        iters = common.split(L, n=2)
        iters[i].next()
        try:
            iters[i].next()
            assert False
        except IndexError as e:
            assert e.args == (i,)

def test_icapture():
    x = range(100)
    y = []
    z = []
    for i in common.icapture(x, result=y):
        z.append(i)
    assert x == y
    assert x == z
