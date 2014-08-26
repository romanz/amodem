#!/usr/bin/env python
import numpy as np
import itertools
import logging

from amodem import common

log = logging.getLogger(__name__)


class Interpolator(object):
    def __init__(self, resolution=10000, width=128):
        self.width = width
        self.resolution = resolution
        N = resolution * width
        u = np.arange(-N, N, dtype=float)
        window = (1 + np.cos(0.5 * np.pi * u / N)) / 2.0
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
    def __init__(self, src, interp=None):
        self.freq = 1.0
        self.equalizer = lambda x: x
        if interp is not None:
            self.interp = interp
            self.resolution = self.interp.resolution
            self.filt = self.interp.filt
            self.width = self.interp.width

            # TODO: explain indices arithmetic
            padding = [0.0] * self.interp.width
            self.src = itertools.chain(padding, src)
            self.offset = self.interp.width + 1
            self.buff = np.zeros(self.interp.coeff_len)
            self.index = 0
            self.take = self._take
        else:
            # skip interpolation
            src = iter(src)
            self.take = lambda size: common.take(src, size)

    def _take(self, size):
        frame = np.zeros(size)
        count = 0
        try:
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
                frame[frame_index] = np.dot(coeffs, self.buff)
                count = frame_index + 1
        except StopIteration:
            pass

        return self.equalizer(frame[:count])


def resample(src, dst, df=0.0):
    from . import common
    x = common.load(src)
    sampler = Sampler(x, Interpolator())
    sampler.freq += df
    y = sampler.take(len(x))
    dst.write(common.dumps(y))
