import itertools
import random

import pytest

from .. import framing


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
    decoded = framing.decode_frames(encoded)
    assert concat(decoded) == data


def test_fail():
    encoded = list(framing.encode(''))
    encoded[-1] = not encoded[-1]
    with pytest.raises(ValueError):
        concat(framing.decode_frames(encoded))


def test_missing():
    f = framing.Framer()
    with pytest.raises(ValueError):
        concat(f.decode(b''))
    with pytest.raises(ValueError):
        concat(f.decode(b'\x01'))
    with pytest.raises(ValueError):
        concat(f.decode(b'\xff'))
