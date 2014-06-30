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
            self.filt.append(h[index::resolution])
        lengths = map(len, self.filt)
        assert set(lengths) == set([2*width])
        assert len(self.filt) == resolution

    def get(self, offset):
        k = int(offset)
        j = np.round((offset - k) * self.resolution)
        index = (self.resolution - int(j)) % self.resolution
        coeffs = self.filt[index]

        offset = int(np.ceil(offset))
        return coeffs, offset - self.width

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
        for s in self.src:
            self.buff.append(s)
            self.index += 1
            if self.index == end:
                self.buff = self.buff[-len(coeffs):]
                return np.dot(coeffs, self.buff)

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
        sampler.freq = 1
        while True:
            u = sampler.sample()
            if u is None:
                break
            y.append(u)
            sampler.next()
        x = np.array(y)

        S = recv.extract_symbols(x, f0)
        S = np.array(list(S))

        y = S #np.array(list(calib(S)))
        pylab.subplot(1,2,1)
        pylab.plot(y.real, y.imag, '.'); pylab.axis('equal')
        pylab.subplot(1,2,2)
        phase = np.unwrap(np.angle(y))

        phase_error_per_1ms = (phase[-1] - phase[0]) / (len(phase) - 1)
        freq_error = phase_error_per_1ms * 1000.0 / (2 * np.pi)
        print freq_error
        pylab.plot(phase)
        pylab.grid('on')
        #pylab.show()
        return

    t = np.arange(64) * common.Ts
    x = np.sin(2 * np.pi * 3.456e3 * t)
    r = Interpolator()

    # pylab.figure()
    y = []
    k = 32 + np.linspace(-5, 5, 1001)
    for offset in k:
        h, i = r.get(offset)
        y.append( np.dot(x[i:i+len(h)], h) )

    pylab.figure()
    pylab.plot(t, x, '.', k * common.Ts, y, '-')
    pylab.show()

if __name__ == '__main__':
    main()
