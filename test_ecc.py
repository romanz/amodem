import ecc
import random

def test_random():
    r = random.Random(0)
    x = bytearray(r.randrange(0, 256) for i in range(16 * 1024))
    y = ecc.encode(x)
    assert len(y) % ecc.BLOCK_SIZE == 0
    x_ = ecc.decode(y)
    assert x_[:len(x)] == x
    assert all(v == 0 for v in x_[len(x):])

def test_file():
    data = open('data.send').read()
    assert ecc.decode(ecc.encode(data)) == data
