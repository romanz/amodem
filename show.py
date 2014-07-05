import pylab
import numpy as np

import sigproc

def constellation(y, title):
    theta = np.linspace(0, 2*np.pi, 1000)
    pylab.plot(y.real, y.imag, '.')
    pylab.plot(np.cos(theta), np.sin(theta), ':')
    points = np.array(sigproc.modulator.points)
    pylab.plot(points.real, points.imag, 'o')
    pylab.grid('on')
    pylab.axis('equal')
    pylab.axis(np.array([-1, 1, -1, 1]) * 1.1)
    pylab.title(title)

def spectrogram(t, x, Fs, NFFT=256):
    ax1 = pylab.subplot(211)
    pylab.plot(t, x)

    pylab.subplot(212, sharex=ax1)
    Pxx, freqs, bins, im = pylab.specgram(x,
        NFFT=NFFT, Fs=Fs, noverlap=NFFT/2, cmap=pylab.cm.gist_heat)

if __name__ == '__main__':
    import sys
    import common

    for fname in sys.argv[1:]:
        t, x = common.load(open(fname, 'rb'))
        pylab.figure()
        pylab.title(fname)
        spectrogram(t, x, common.Fs)

    pylab.show()

