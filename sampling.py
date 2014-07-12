import numpy as np
import itertools
import logging

log = logging.getLogger(__name__)


class Interpolator(object):
    def __init__(self, resolution=10000, width=128):
        self.width = width
        self.resolution = resolution
        self.N = resolution * width
        u = np.arange(-self.N, self.N, dtype=float)
        window = (1 + np.cos(0.5 * np.pi * u / self.N)) / 2.0
        h = np.sinc(u / resolution) * window
        self.filt = []
        for index in range(resolution):  # split into multiphase filters
            filt = h[index::resolution]
            filt = filt[::-1]
            self.filt.append(filt)
        lengths = map(len, self.filt)
        self.coeff_len = 2*width
        assert set(lengths) == set([self.coeff_len])
        assert len(self.filt) == resolution

    def get(self, offset):
        # offset = k + (j / self.resolution)
        k = int(offset)
        j = int((offset - k) * self.resolution)
        coeffs = self.filt[j]
        return coeffs, k - self.width


class Sampler(object):
    def __init__(self, src, interp=None):
        self.freq = 1.0
        self.interp = interp if (interp is not None) else Interpolator()

        # TODO: explain indices arithmetic
        padding = [0.0] * (self.interp.width - 1)
        self.src = itertools.chain(padding, src)
        self.offset = self.interp.width + 1
        self.buff = np.zeros(self.interp.coeff_len)
        self.index = 0

    def __iter__(self):
        return self

    def correct(self, offset=0):
        assert self.freq + offset > 0
        self.offset += offset

    def next(self):
        res = self._sample()
        self.offset += self.freq
        return res

    def _sample(self):
        coeffs, begin = self.interp.get(self.offset)
        end = begin + self.interp.coeff_len
        while True:
            if self.index == end:
                return np.dot(coeffs, self.buff)

            self.buff[:-1] = self.buff[1:]
            self.buff[-1] = self.src.next()  # throws StopIteration
            self.index += 1

if __name__ == '__main__':
    import common
    import sys
    df, = sys.argv[1:]
    df = float(df)

    _, x = common.load(sys.stdin)
    sampler = Sampler(x, Interpolator())
    sampler.freq += df
    y = np.array(list(sampler))
    y = common.dumps(y*1j)
    sys.stdout.write(y)
