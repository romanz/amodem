''' Reed-Solomon CODEC. '''
from reedsolo import rs_encode_msg, rs_correct_msg, ReedSolomonError

import struct
import logging
log = logging.getLogger(__name__)

DEFAULT_NSYM = 10
BLOCK_SIZE = 255

LEN_FMT = '<I'

def encode(data, nsym=DEFAULT_NSYM):
    log.debug('Encoded {} bytes'.format(len(data)))
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
            log.debug('Decoded %d blocks = %d bytes', (i+1) / BLOCK_SIZE, len(dec))
        except ReedSolomonError as e:
            log.debug('Decoding stopped: %s', e)
            break

    if i == 0:
        return None

    overhead = (i - len(dec)) / float(i)
    blocks = i / BLOCK_SIZE
    log.debug('Decoded %d blocks = %d bytes (ECC overhead %.1f%%)', blocks, len(dec), overhead * 100)

    n = struct.calcsize(LEN_FMT)
    payload, length = dec[n:], dec[:n]
    length, = struct.unpack(LEN_FMT, length)
    if length > len(payload):
        log.warning('%d bytes are missing!', length - len(payload))
        return None

    return payload[:length]
