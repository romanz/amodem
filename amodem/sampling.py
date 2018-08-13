import itertools

import numpy as np

from . import common


class Interpolator:

    def __init__(self, resolution=1024, width=128):

        self.width = width
        self.resolution = resolution

        N = resolution * width
        u = np.arange(-N, N, dtype=float)
        window = np.cos(0.5 * np.pi * u / N) ** 2.0  # raised cosine

        h = np.sinc(u / resolution) * window
        self.filt = []
        for index in range(resolution):  # split into multiphase filters
            filt = h[index::resolution]
            filt = filt[::-1]  # flip (due to convolution)
            self.filt.append(filt)

        lengths = [len(f) for f in self.filt]
        self.coeff_len = 2 * width

        assert set(lengths) == set([self.coeff_len])  # verify same lengths
        assert len(self.filt) == resolution


defaultInterpolator = Interpolator()


class Sampler:
    def __init__(self, src, interp=None, freq=1.0):
        self.freq = freq
        self.equalizer = lambda x: x  # LTI equalization filter
        if interp is not None:
            self.interp = interp
            self.resolution = self.interp.resolution
            self.filt = self.interp.filt
            self.width = self.interp.width

            # polyphase filters are centered at (width + 1) index
            padding = [0.0] * self.interp.width
            # pad with zeroes to "simulate" regular sampling
            self.src = itertools.chain(padding, src)
            self.offset = self.interp.width + 1
            # samples' buffer to be used by interpolation
            self.buff = np.zeros(self.interp.coeff_len)
            self.index = 0
            self.take = self._take
        else:
            # skip interpolation (for testing)
            src = iter(src)
            self.take = lambda size: common.take(src, size)

    def _take(self, size):
        frame = np.zeros(size)
        count = 0
        for frame_index in range(size):
            offset = self.offset
            # offset = k + (j / self.resolution)
            k = int(offset)  # integer part
            j = int((offset - k) * self.resolution)  # fractional part
            coeffs = self.filt[j]  # choose correct filter phase
            end = k + self.width
            # process input until all buffer is full with samples
            try:
                while self.index < end:
                    self.buff[:-1] = self.buff[1:]
                    self.buff[-1] = next(self.src)  # throws StopIteration
                    self.index += 1
            except StopIteration:
                break

            self.offset += self.freq
            # apply interpolation filter
            frame[frame_index] = np.dot(coeffs, self.buff)
            count = frame_index + 1

        return self.equalizer(frame[:count])


def resample(src, dst, df=0.0):
    x = common.load(src)
    sampler = Sampler(x, Interpolator())
    sampler.freq += df
    y = sampler.take(len(x))
    dst.write(common.dumps(y))
