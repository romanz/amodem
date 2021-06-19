""" Common package functionality.
Commom utilities and procedures for amodem.

"""

import itertools
import logging

import numpy as np

log = logging.getLogger(__name__)

scaling = 32000.0  # out of 2**15


def load(fileobj):
    """ Load signal from file object. """
    return loads(fileobj.read())


def loads(data):
    """ Load signal from memory buffer. """
    x = np.frombuffer(data, dtype='int16')
    x = x / scaling
    return x


def dumps(sym):
    """ Dump signal to memory buffer. """
    sym = sym.real * scaling
    return sym.astype('int16').tostring()


def iterate(data, size, func=None, truncate=True, index=False):
    """ Iterate over a signal, taking each time *size* elements. """
    offset = 0
    data = iter(data)

    done = False
    while not done:
        buf = list(itertools.islice(data, size))
        if len(buf) < size:
            if truncate or not buf:
                return
            done = True

        result = func(buf) if func else np.array(buf)
        yield (offset, result) if index else result
        offset += size


def split(iterable, n):
    """ Split an iterable of n-tuples into n iterables of scalars.
    The k-th iterable will be equivalent to (i[k] for i in iter).
    """
    def _gen(it, index):
        for item in it:
            yield item[index]

    iterables = itertools.tee(iterable, n)
    return [_gen(it, index) for index, it in enumerate(iterables)]


def icapture(iterable, result):
    """ Appends each yielded item to result. """
    for i in iter(iterable):
        result.append(i)
        yield i


def take(iterable, n):
    """ Take n elements from iterable, and return them as a numpy array. """
    return np.array(list(itertools.islice(iterable, n)))


class Dummy:
    """ Dummy placeholder object for testing and mocking. """

    def __getattr__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        return self
