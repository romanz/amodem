import numpy as np

import recv
import common
import sigproc
import sampling
import loop

class FreqLoop(object):
    def __init__(self, x, freq):
        self.sampler = sampling.Sampler(x, sampling.Interpolator())
        self.symbols = recv.extract_symbols(self.sampler, freq)
        Kp, Ki = 0.2, 0.01
        b = np.array([1, -1])*Kp + np.array([0.5, 0.5])*Ki
        self.filt = loop.Filter(b=b, a=[1])
        self.correction = 0.0

    def correct(self, actual, expected):
        self.err = np.angle(expected / actual) / np.pi
        self.err = sigproc.clip(self.err, [-0.1, 0.1])
        self.correction = self.filt(self.err)
        self.sampler.correct(offset=self.correction)

    def __iter__(self):
        return iter(self.symbols)

import pylab

def main():
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

    S = np.array(S)

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
