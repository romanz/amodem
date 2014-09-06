from amodem import framing
import random
import itertools

import pytest


def concat(iterable):
    return bytearray(itertools.chain.from_iterable(iterable))

r = random.Random(0)
blob = bytearray(r.randrange(0, 256) for i in range(64 * 1024))


@pytest.fixture(params=[b'', b'abc', b'1234567890', blob, blob[:12345]])
def data(request):
    return request.param


def test_checksum(data):
    c = framing.Checksum()
    assert c.decode(c.encode(data)) == data


def test_framer(data):
    f = framing.Framer()
    encoded = concat(f.encode(data))
    decoded = concat(f.decode(encoded))
    assert decoded == data


def test_main(data):
    encoded = framing.encode(data)
    decoded = framing.decode(encoded)
    assert bytearray(decoded) == data
