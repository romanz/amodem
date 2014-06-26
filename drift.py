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

    def get(self, x, offset):
        k = int(offset)
        j = np.round((offset - k) * self.resolution)
        h = self.filt[(self.resolution - int(j)) % self.resolution]

        offset = np.ceil(offset)
        begin, end = offset - self.width, offset + self.width
        return np.dot(h, x[begin:end])

class Sampler(object):
    def __init__(self, src, frame_size):
        self.src = src
        self.freq = 1.0
        self.offset = 0
        self.frame_size = frame_size
        self.buff = []

    def frame(self):
        self.buff.extend()


    def

if __name__ == '__main__':
    import pylab
    if 0:
        f0 = 10e3
        t, x = common.load('recv_10kHz.pcm')
        S = recv.extract_symbols(x, f0)
        S = np.array(list(S))

        y = S #np.array(list(calib(S)))
        pylab.subplot(1,2,1)
        pylab.plot(y.real, y.imag, '.'); pylab.axis('equal')
        pylab.subplot(1,2,2)
        pylab.plot(np.unwrap(np.angle(y)))
        pylab.grid('on')

    t = np.arange(64) * common.Ts
    x = np.sin(2 * np.pi * 3.456e3 * t)
    r = Interpolator()

    # pylab.figure()
    y = []
    k = 32 + np.linspace(-5, 5, 1001)
    for offset in k:
        y.append( r.get(x, offset) )

    pylab.figure()
    pylab.plot(t, x, '.', k * common.Ts, y, '-')
    pylab.show()
