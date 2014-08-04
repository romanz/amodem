import numpy as np
import pylab

import common
import loop

t = np.arange(0.1*common.Fs) * common.Ts
f = common.Fc * (1 + 10e-6)
x = np.sin(2*np.pi*f*t)
fl = loop.FreqLoop(iter(x), [common.Fc])

S = []
gain = common.Nsym / (2*np.pi)
for s, in fl:
    y = np.round(s)
    if abs(y) > 0:
        err = -np.angle(s / y) * gain
        S.append([err])
        fl.sampler.offset += 0.5*err

S = np.array(S)
pylab.plot(S)
pylab.show()
