from amodem import ecc
import random
import itertools
import reedsolo


def concat(chunks):
    return bytearray(itertools.chain.from_iterable(chunks))


def test_random():
    r = random.Random(0)
    x = bytearray(r.randrange(0, 256) for i in range(64 * 1024))
    y = ecc.encode(x)
    x_ = concat(ecc.decode(y))
    assert x_ == x


def test_errors():
    data = bytearray(range(244))
    blocks = list(ecc.encode(data))
    assert len(blocks) == 2
    for i in range(ecc.DEFAULT_NSYM // 2):
        blocks[0][i] = blocks[0][i] ^ 0xFF

    i = ecc.DEFAULT_NSYM // 2
    try:
        blocks[0][i] = blocks[0][i] ^ 0xFF
        concat(ecc.decode(blocks))
        assert False
    except reedsolo.ReedSolomonError as e:
        assert e.args == ('Too many errors to correct',)
