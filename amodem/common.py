import functools
import itertools
import numpy as np

import logging
log = logging.getLogger(__name__)

scaling = 32000.0  # out of 2**15
SATURATION_THRESHOLD = 1.0

LENGTH_FORMAT = '<I'


def to_bits(bytes_list):
    for val in bytes_list:
        for i in range(8):
            mask = 1 << i
            yield (1 if (val & mask) else 0)

bit_weights = [1 << i for i in range(8)]


def to_byte(bits):
    assert len(bits) == 8
    byte = int(np.dot(bits, bit_weights))
    return chr(byte)


class SaturationError(ValueError):
    pass


def check_saturation(x):
    peak = np.max(np.abs(x))
    if peak > SATURATION_THRESHOLD:
        raise SaturationError(peak)


def load(fileobj):
    return loads(fileobj.read())


def loads(data):
    x = np.fromstring(str(data), dtype='int16')
    x = x / scaling
    return x


def dumps(sym, n=1):
    sym = sym.imag * scaling
    sym = sym.astype('int16')
    data = sym.tostring()
    return data * n


def iterate(data, size, func=None, truncate=True):
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
        yield offset, result
        offset += size


class Splitter(object):

    def __init__(self, iterable, n):
        self.iterable = iter(iterable)
        self.read = [True] * n
        self.last = None
        self.generators = [functools.partial(self._gen, i)() for i in range(n)]
        self.n = n

    def _gen(self, index):
        while True:
            if all(self.read):
                try:
                    self.last = self.iterable.next()
                except StopIteration:
                    return

                assert len(self.last) == self.n
                self.read = [False] * self.n

            if self.read[index]:
                raise IndexError(index)
            self.read[index] = True
            yield self.last[index]


def split(iterable, n):
    return Splitter(iterable, n).generators


def icapture(iterable, result):
    for i in iter(iterable):
        result.append(i)
        yield i


def take(iterable, n):
    return np.array(list(itertools.islice(iterable, n)))


try:
    izip = itertools.izip
except AttributeError:
    izip = zip  # Python 3
