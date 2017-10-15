#!/usr/bin/env python

"""Script that exposes pylab's spectogram plotting
capabilities to the command line. It implements this
for amodem.config Configurations.

"""

import pylab
import numpy as np
from amodem import common
from amodem.config import Configuration
import sys


def spectrogram(t, x, Fs, NFFT=256):
    ax1 = pylab.subplot(211)
    pylab.plot(t, x)

    pylab.subplot(212, sharex=ax1)
    pylab.specgram(x, NFFT=NFFT, Fs=Fs, noverlap=NFFT/2,
                   cmap=pylab.cm.gist_heat)


def main():
    config = Configuration()

    for fname in sys.argv[1:]:
        x = common.load(open(fname, 'rb'))
        t = np.arange(len(x)) * config.Ts
        pylab.figure()
        pylab.title(fname)
        spectrogram(t, x, config.Fs)

    pylab.show()


if __name__ == '__main__':
    main()
