import numpy as np

import recv
import common
import loop

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
        assert set(lengths) == set([2*width])
        assert len(self.filt) == resolution

    def get(self, offset):
        # offset = k + (j / self.resolution)
        k = int(offset)
        j = int((offset - k) * self.resolution)
        coeffs = self.filt[j]
        return coeffs, k - self.width

class Sampler(object):
    def __init__(self, src, interp):
        self.src = iter(src)
        self.freq = 1.0
        self.interp = interp
        coeffs, begin = self.interp.get(0)
        self.offset = -begin  # should fill samples buffer
        self.buff = np.zeros(len(coeffs))
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
        end = begin + len(coeffs)
        while True:
            if self.index == end:
                return np.dot(coeffs, self.buff)

            self.buff[:-1] = self.buff[1:]
            self.buff[-1] = self.src.next()
            self.index += 1

def clip(x, lims):
    return min(max(x, lims[0]), lims[1])

def loop_filter(P, I):
    return loop.Filter(b=[P*(1+I/2.), P*(-1+I/2.)], a=[1])

def main():
    import pylab

    f0 = 10e3
    _, x = common.load('recv_10kHz.pcm')
    x = x[100:]
    sampler = Sampler(x, Interpolator())
    S = []
    first = None
    Y = []

    filt = loop_filter(P=0.1, I=0.01)
    for s in recv.extract_symbols(sampler, f0):
        S.append(s)
        if first is None:
            first = s
        else:
            err = np.angle(first / s) / (2*np.pi)
            err = clip(err, [-0.1, 0.1])
            filt_err = filt(err)
            sampler.correct(offset=filt_err)
            Y.append([err, filt_err])


    y = np.array(list(S))

    pylab.figure()
    pylab.subplot(121)
    pylab.plot(y.real, y.imag, '.')
    pylab.grid('on')
    pylab.axis('equal')
    pylab.subplot(122)
    pylab.plot(np.array(Y) * 1e3 / 32, '-')
    pylab.grid('on')
    pylab.show()
    return

if __name__ == '__main__':
    main()

