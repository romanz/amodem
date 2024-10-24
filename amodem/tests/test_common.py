import numpy as np

from .. import common, config


def iterlist(x, *args, **kwargs):
    x = np.array(x)
    return list(
        (i, list(x))
        for i, x in common.iterate(x, index=True, *args, **kwargs)
    )


def test_iterate():
    N = 10
    assert iterlist(range(N), 1) == [
        (i, [i]) for i in range(N)]

    assert iterlist(range(N), 2) == [
        (i, [i, i+1]) for i in range(0, N-1, 2)]

    assert iterlist(range(N), 3) == [
        (i, [i, i+1, i+2]) for i in range(0, N-2, 3)]

    assert iterlist(range(N), 1, func=lambda b: -np.array(b)) == [
        (i, [-i]) for i in range(N)]


def test_split():
    L = [(i*2, i*2+1) for i in range(10)]
    iters = common.split(L, n=2)
    assert list(zip(*iters)) == L


def test_icapture():
    x = range(100)
    y = []
    z = []
    for i in common.icapture(x, result=y):
        z.append(i)
    assert list(x) == y
    assert list(x) == z


def test_dumps_loads():
    x = np.array([.1, .4, .2, .6, .3, .5])
    y = common.loads(common.dumps(x))
    assert all(x == y)


def test_configs():
    default = config.Configuration()
    fastest = config.fastest()
    slowest = config.slowest()
    assert slowest.modem_bps <= default.modem_bps
    assert fastest.modem_bps >= default.modem_bps
