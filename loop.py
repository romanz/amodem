import numpy as np
import itertools

import recv
import sampling
import sigproc

class Filter(object):
    def __init__(self, b, a=()):
        self.b = b
        self.a = a
        self.x = [0] * len(b)
        self.y = [0] * len(a)

    def __call__(self, x):
        self.x = [x] + self.x
        self.x = self.x[:len(self.b)]
        self.y = self.y[:len(self.a)]
        y = np.dot(self.x, self.b) + np.dot(self.y, self.a)
        self.y = [y] + self.y
        return y

class FreqLoop(object):
    def __init__(self, x, freqs):
        self.sampler = sampling.Sampler(x, sampling.Interpolator())
        self.gens = []

        gens = itertools.tee(self.sampler, len(freqs))
        for freq, gen in zip(freqs, gens):
            self.gens.append( recv.extract_symbols(self.sampler, freq) )

        Kp, Ki = 0.2, 0.01
        b = np.array([1, -1])*Kp + np.array([0.5, 0.5])*Ki
        self.filt = Filter(b=b, a=[1])
        self.correction = 0.0

    def correct(self, actual, expected):
        self.err = np.angle(expected / actual) / np.pi
        self.err = sigproc.clip(self.err, [-0.1, 0.1])
        self.correction = self.filt(self.err)
        self.sampler.correct(offset=self.correction)

    def __iter__(self):
        return itertools.izip(*self.gens)
