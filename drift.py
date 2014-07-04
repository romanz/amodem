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
            self.buff[-1] = self.src.next()  # throws StopIteration
            self.index += 1

def clip(x, lims):
    return min(max(x, lims[0]), lims[1])

def loop_filter(P, I):
    return

class FreqLoop(object):
    def __init__(self, x, freq):
        self.sampler = Sampler(x, Interpolator())
        self.symbols = recv.extract_symbols(self.sampler, freq)
        Kp, Ki = 0.2, 0.01
        b = np.array([1, -1])*Kp + np.array([0.5, 0.5])*Ki
        self.filt = loop.Filter(b=b, a=[1])
        self.correction = 0.0

    def correct(self, actual, expected):
        self.err = np.angle(expected / actual) / np.pi
        self.err = clip(self.err, [-0.1, 0.1])
        self.correction = self.filt(self.err)
        self.sampler.correct(offset=self.correction)

    def __iter__(self):
        return iter(self.symbols)

import pylab

def main():
    import sigproc

    f0 = 10e3
    _, x = common.load('recv_10kHz.pcm')
    x = x[100:]

    S = []
    Y = []

    symbols = FreqLoop(x, f0)
    prefix = 100
    for s in symbols:
        S.append(s)
        if len(S) > prefix:
            symbols.correct(s, np.mean(S[:prefix]))
        Y.append([
            symbols.correction * (f0 / common.Nsym),
        ])

    S = np.array(list(S))

    pylab.figure()

    pylab.subplot(121)
    circle = np.exp(2j*np.pi*np.linspace(0, 1, 1001))
    pylab.plot(S.real, S.imag, '.', circle.real, circle.imag, ':')
    pylab.grid('on')
    pylab.axis('equal')

    Y = np.array(Y)
    a = 0.01
    pylab.subplot(122)
    pylab.plot(list(sigproc.lfilter([a], [1, a-1], Y)), '-')
    pylab.grid('on')

if __name__ == '__main__':
    main()
    pylab.show()
