import ecc
import random
import itertools


def concat(chunks):
    return bytearray(itertools.chain.from_iterable(chunks))


def test_random():
    r = random.Random(0)
    x = bytearray(r.randrange(0, 256) for i in range(64 * 1024))
    y = ecc.encode(x)
    x_ = concat(ecc.decode(y))
    assert x_ == x
