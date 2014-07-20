''' Reed-Solomon CODEC. '''
from reedsolo import rs_encode_msg, rs_correct_msg

import logging
log = logging.getLogger(__name__)

import common

DEFAULT_NSYM = 10
BLOCK_SIZE = 255


def end_of_stream(size):
    return bytearray([BLOCK_SIZE]) + b'\x00' * size


def encode(data, nsym=DEFAULT_NSYM):
    chunk_size = BLOCK_SIZE - nsym - 1

    enc = bytearray()
    for i in range(0, len(data), chunk_size):
        chunk = bytearray(data[i:i+chunk_size])

        size = len(chunk)
        if size < chunk_size:
            padding = b'\x00' * (chunk_size - size)
            chunk.extend(padding)

        chunk = bytearray([size]) + chunk
        enc.extend(rs_encode_msg(chunk, nsym))

    enc.extend(rs_encode_msg(end_of_stream(chunk_size), nsym))
    return enc


def decode(data, nsym=DEFAULT_NSYM):

    last_chunk = end_of_stream(BLOCK_SIZE - nsym - 1)
    for _, block in common.iterate(data, BLOCK_SIZE):
        chunk = bytearray(rs_correct_msg(block, nsym))
        if chunk == last_chunk:
            return  # end of stream

        size = chunk[0]
        payload = chunk[1:]
        if size > len(payload):
            raise ValueError('Invalid chunk', size, len(payload), payload)

        yield payload[:size]
