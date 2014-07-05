import numpy as np
import pylab

import common
import sigproc
import loop

def main():
    f0 = 10e3
    _, x = common.load(file('recv_10kHz.pcm', 'rb'))
    x = x[100:]

    S = []
    Y = []

    prefix = 100
    symbols = loop.FreqLoop(x, [f0])
    for s, in symbols:
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
