import itertools
import numpy as np

import logging
log = logging.getLogger(__name__)

scaling = 32000.0  # out of 2**15
SATURATION_THRESHOLD = (2**15 - 1) / scaling


class SaturationError(ValueError):
    pass


def check_saturation(x):
    peak = np.max(np.abs(x))
    if peak >= SATURATION_THRESHOLD:
        raise SaturationError(peak)


def load(fileobj):
    return loads(fileobj.read())


def loads(data):
    x = np.frombuffer(data, dtype='int16')
    x = x / scaling
    return x


def dumps(sym, n=1):
    sym = sym.real * scaling
    sym = sym.astype('int16')
    data = sym.tostring()
    return data * n


def iterate(data, size, func=None, truncate=True, enumerate=False):
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
        yield (offset, result) if enumerate else result
        offset += size


def split(iterable, n):
    def _gen(it, index):
        for item in it:
            yield item[index]

    iterables = itertools.tee(iterable, n)
    return [_gen(it, index) for index, it in enumerate(iterables)]


def icapture(iterable, result):
    for i in iter(iterable):
        result.append(i)
        yield i


def take(iterable, n):
    return np.array(list(itertools.islice(iterable, n)))


# "Python 3" zip re-implementation for Python 2
def izip(iterables):
    iterables = [iter(iterable) for iterable in iterables]
    while True:
        yield tuple([next(iterable) for iterable in iterables])


class Dummy(object):

    def __getattr__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        return self
