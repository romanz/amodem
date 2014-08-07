''' Reed-Solomon CODEC. '''
from reedsolo import rs_encode_msg, rs_correct_msg

from . import common

import logging
log = logging.getLogger(__name__)

DEFAULT_NSYM = 10
BLOCK_SIZE = 255


def end_of_stream(size):
    return bytearray([BLOCK_SIZE]) + b'\x00' * size


def encode(data, nsym=DEFAULT_NSYM):
    chunk_size = BLOCK_SIZE - nsym - 1

    for _, chunk in common.iterate(data=data, size=chunk_size,
                                   func=bytearray, truncate=False):
        size = len(chunk)
        if size < chunk_size:
            padding = [0] * (chunk_size - size)
            chunk.extend(padding)

        block = bytearray([size]) + chunk
        yield rs_encode_msg(block, nsym)

    yield rs_encode_msg(end_of_stream(chunk_size), nsym)


def decode(blocks, nsym=DEFAULT_NSYM):

    last_chunk = end_of_stream(BLOCK_SIZE - nsym - 1)
    for block in blocks:
        assert len(block) == BLOCK_SIZE
        chunk = bytearray(rs_correct_msg(block, nsym))
        if chunk == last_chunk:
            log.info('EOF encountered')
            return  # end of stream

        size = chunk[0]
        payload = chunk[1:]
        if size > len(payload):
            raise ValueError('Invalid chunk', size, len(payload), payload)

        yield payload[:size]
