#!/usr/bin/env python
import pylab
import numpy as np


def spectrogram(t, x, Fs, NFFT=256):
    ax1 = pylab.subplot(211)
    pylab.plot(t, x)

    pylab.subplot(212, sharex=ax1)
    pylab.specgram(x, NFFT=NFFT, Fs=Fs, noverlap=NFFT/2,
                   cmap=pylab.cm.gist_heat)

if __name__ == '__main__':
    import sys
    from amodem import common
    from amodem.config import Fs, Ts

    for fname in sys.argv[1:]:
        x = common.load(open(fname, 'rb'))
        t = np.arange(len(x)) * Ts
        pylab.figure()
        pylab.title(fname)
        spectrogram(t, x, Fs)

    pylab.show()
