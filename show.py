def spectrogram(t, x):
    ax1 = pylab.subplot(211)
    pylab.plot(t, x)

    pylab.subplot(212, sharex=ax1)
    Pxx, freqs, bins, im = pylab.specgram(x,
        NFFT=NFFT, Fs=Fs, noverlap=NFFT/2, cmap=pylab.cm.gist_heat)

    pylab.show()
