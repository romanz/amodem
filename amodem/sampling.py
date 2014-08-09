#!/usr/bin/env python
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


class Sampler(object):
    def __init__(self, src, interp):
        self.freq = 1.0
        self.interp = interp
        self.resolution = self.interp.resolution
        self.filt = self.interp.filt
        self.width = self.interp.width

        # TODO: explain indices arithmetic
        padding = [0.0] * (self.interp.width - 1)
        self.src = itertools.chain(padding, src)
        self.offset = self.interp.width + 1
        self.buff = np.zeros(self.interp.coeff_len)
        self.index = 0
        self.gain = 1.0

    def take(self, size):
        frame = np.zeros(size)

        for frame_index in range(size):
            offset = self.offset
            # offset = k + (j / self.resolution)
            k = int(offset)  # integer part
            j = int((offset - k) * self.resolution)  # fractional part
            coeffs = self.filt[j]
            end = k + self.width
            while self.index < end:
                self.buff[:-1] = self.buff[1:]
                self.buff[-1] = next(self.src)  # throws StopIteration
                self.index += 1

            self.offset += self.freq
            frame[frame_index] = np.dot(coeffs, self.buff) * self.gain

        return frame


if __name__ == '__main__':
    import common
    import sys
    df, = sys.argv[1:]
    df = float(df)

    x = common.load(sys.stdin)
    sampler = Sampler(x, Interpolator())
    sampler.freq += df
    y = np.array(list(sampler))
    y = common.dumps(y)
    sys.stdout.write(y)
