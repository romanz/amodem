import pylab

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
        t, x = common.load(fname)
        pylab.figure()
        pylab.title(fname)
        spectrogram(t, x, common.Fs)

    pylab.show()

