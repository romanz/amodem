import numpy as np
import itertools

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
    def __init__(self, src, freqs):
        interp = sampling.Interpolator()
        self.sampler = sampling.Sampler(src, interp)
        self.gens = []

        samplers = itertools.tee(self.sampler, len(freqs))
        for freq, generator in zip(freqs, samplers):
            gen = sigproc.extract_symbols(generator, freq)
            self.gens.append(gen)

    def __iter__(self):
        return itertools.izip(*self.gens)
