import ecc
import random
import itertools


def concat(chunks):
    return bytearray(itertools.chain.from_iterable(chunks))


def test_random():
    r = random.Random(0)
    x = bytearray(r.randrange(0, 256) for i in range(16 * 1024))
    y = ecc.encode(x)
    assert len(y) % ecc.BLOCK_SIZE == 0
    x_ = concat(ecc.decode(y))
    assert x_[:len(x)] == x
    assert all(v == 0 for v in x_[len(x):])


def test_file():
    data = open('data.send').read()
    enc = ecc.encode(data)
    assert concat(ecc.decode(enc)) == data
