''' Reed-Solomon CODEC. '''
from reedsolo import rs_encode_msg, rs_correct_msg, ReedSolomonError

import struct
import logging
log = logging.getLogger(__name__)

DEFAULT_NSYM = 25
BLOCK_SIZE = 255

LEN_FMT = '<I'

def encode(data, nsym=DEFAULT_NSYM):
    log.info('Encoded {} bytes'.format(len(data)))
    data = bytearray(struct.pack(LEN_FMT, len(data)) + data)
    chunk_size = BLOCK_SIZE - nsym
    enc = bytearray()
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        if len(chunk) < chunk_size:
            padding = b'\x00' * (chunk_size - len(chunk))
            chunk.extend(padding)
        enc.extend(rs_encode_msg(chunk, nsym))

    return enc

def decode(data, nsym=DEFAULT_NSYM):
    data = bytearray(data)
    dec = bytearray()
    for i in range(0, len(data), BLOCK_SIZE):
        chunk = data[i:i+BLOCK_SIZE]
        try:
            dec.extend(rs_correct_msg(chunk, nsym))
        except ReedSolomonError:
            break

    overhead = (i - len(dec)) / float(i)
    blocks = i / BLOCK_SIZE
    log.debug('Decoded %d blocks = %d bytes (ECC overhead %.1f%%)', blocks, len(dec), overhead * 100)

    n = struct.calcsize(LEN_FMT)
    payload, length = dec[n:], dec[:n]
    length, = struct.unpack(LEN_FMT, length)
    assert length <= len(payload)
    log.info('Decoded {} bytes'.format(length))
    return payload[:length]


def test_codec():
    import random
    r = random.Random(0)
    x = bytearray(r.randrange(0, 256) for i in range(16 * 1024))
    y = encode(x)
    assert len(y) % BLOCK_SIZE == 0
    x_ = decode(y)
    assert x_[:len(x)] == x
    assert all(v == 0 for v in x_[len(x):])
