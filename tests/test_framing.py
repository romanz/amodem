from amodem import framing
import random
import itertools
import reedsolo


def concat(chunks):
    return bytearray(itertools.chain.from_iterable(chunks))


def test_random():
    r = random.Random(0)
    x = bytearray(r.randrange(0, 256) for i in range(64 * 1024))
    y = framing.encode(x)
    x_ = concat(framing.decode(y))
    assert x_ == x


def test_errors():
    data = bytearray(range(244))
    blocks = list(framing.encode(data))
    assert len(blocks) == 2
    for i in range(framing.DEFAULT_NSYM // 2):
        blocks[0][i] = blocks[0][i] ^ 0xFF

    i = framing.DEFAULT_NSYM // 2
    try:
        blocks[0][i] = blocks[0][i] ^ 0xFF
        concat(framing.decode(blocks))
        assert False
    except reedsolo.ReedSolomonError as e:
        assert e.args == ('Too many errors to correct',)
