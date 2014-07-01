import numpy as np
import itertools

import recv
import common

class Filter(object):
    def __init__(self, b, a):
        self.b = b
        self.a = a
        self.x = [0] * len(b)
        self.y = [0] * len(a)

    def __call__(self, x):
        self.x = [x] + self.x[:-1]
        assert len(self.x) == len(self.b)
        assert len(self.y) == len(self.a)
        y = np.dot(self.x, self.b) - np.dot(self.y, self.a)
        self.y = [y] + self.y[:-1]
        return y

def overlap_iter(x, n, overlap=0):
    assert overlap >= 0
    assert overlap < n
    res = []
    x = iter(x)
    while True:
        res.extend(itertools.islice(x, n - len(res)))
        if len(res) < n:
            break
        yield tuple(res)
        res = res[n - overlap:]

def test_overlap():
    assert list(overlap_iter(range(7), 3, 1)) == [(0,1,2), (2,3,4), (4,5,6)]
    assert list(overlap_iter(range(7), 3, 0)) == [(0,1,2), (3,4,5)]

def calib(S):
    for S0, S1 in overlap_iter(S, 2, overlap=1):
        dS = S1 / S0
        yield dS

class Interpolator(object):
    def __init__(self, resolution=1000, width=20):
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
    def __init__(self, src, interp=None):
        self.src = iter(src)
        self.index = 0
        self.freq = 1.0
        self.interp = interp or Interpolator()
        self.offset = self.interp.width
        self.buff = []

    def sample(self):
        coeffs, begin = self.interp.get(self.offset)
        end = begin + len(coeffs)
        # C = ', '.join(['%.3f' % c for c in coeffs[18:23]])
        # print '%.3f [%s] %d %d' % (self.offset, C, begin, end)
        while True:
            if self.index == end:
                self.buff = self.buff[-len(coeffs):]
                return np.dot(coeffs, self.buff)
            try:
                s = self.src.next()
            except StopIteration:
                break

            self.buff.append(s)
            self.index += 1

    def next(self):
        self.offset += self.freq


def main():
    import pylab
    if 1:
        f0 = 10e3
        _, x = common.load('recv_10kHz.pcm')
        x = x[100:]
        y = []
        sampler = Sampler(x)
        sampler.freq = 1.0 + 0.112/f0
        while True:
            u = sampler.sample()
            if u is None:
                break
            y.append(u)
            sampler.next()
        x_ = np.array(y)
        S = recv.extract_symbols(x_, f0)
        S = np.array(list(S))

        y = S #np.array(list(calib(S)))
        phase = np.unwrap(np.angle(y))

        phase_error = (phase[-1] - phase[0])
        phase_error_per_1ms =  phase_error / (len(phase) - 1)
        freq_error = phase_error_per_1ms * 1000.0 / (2 * np.pi)
        print phase_error, len(phase)
        print phase_error_per_1ms
        print freq_error

        if 1:
            pylab.figure()
            pylab.plot(y.real, y.imag, '.')
            pylab.grid('on')
        pylab.show()
        return

    I = Interpolator()
    f = I.filt
    pylab.figure()
    pylab.plot(zip(*f[::100]))
    pylab.show()

if __name__ == '__main__':
    main()

