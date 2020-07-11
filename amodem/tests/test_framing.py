from amodem import framing
import random
import itertools

import pytest


def concat(iterable):
    return bytearray(itertools.chain.from_iterable(iterable))


r = random.Random(0)
blob = bytearray(r.randrange(0, 256) for i in range(64 * 1024))
data_fixture_params = [b"", b"abc", b"1234567890", blob, blob[:12345]]


def test_checksum():
    for data in data_fixture_params:
        c = framing.Checksum()
        assert c.decode(c.encode(data)) == data


def test_framer():
    for data in data_fixture_params:
        f = framing.Framer()
        encoded = concat(f.encode(data))
        decoded = concat(f.decode(encoded))
        assert decoded == data


def test_main():
    for data in data_fixture_params:
        encoded = framing.encode(data)
        decoded = framing.decode_frames(encoded)
        assert concat(decoded) == data


def test_fail():
    encoded = list(framing.encode(""))
    encoded[-1] = not encoded[-1]
    with pytest.raises(ValueError):
        concat(framing.decode_frames(encoded))


def test_sequenceError():
    f = framing.Framer(block_size=7)
    encoded14 = concat(f.encode(b"123456789012345678901"))
    footerLen = len(concat(f.encode(b"")))
    blockLenBytes = int((len(encoded14) - footerLen) / 3)
    badEncoded14 = encoded14[:blockLenBytes] + encoded14[2 * blockLenBytes:]
    with pytest.raises(ValueError):
        concat(f.decode(badEncoded14))


def test_missing():
    f = framing.Framer()
    with pytest.raises(ValueError):
        concat(f.decode(b""))
    with pytest.raises(ValueError):
        concat(f.decode(b"\x01"))
    with pytest.raises(ValueError):
        concat(f.decode(b"\xff"))
