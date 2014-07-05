import sigproc
import itertools
import common
import show
import pylab
import numpy as np

def test_qam():
    q = sigproc.QAM(bits_per_symbol=8, radii=[0.25, 0.5, 0.75, 1.0])
    bits = [(1,1,0,1,0,0,1,0), (0,1,0,0,0,1,1,1)]
    stream = itertools.chain(*bits)
    S = q.encode(list(stream))
    decoded = list(q.decode(list(S)))
    assert decoded == bits

def test_drift():
    fc = 10e3
    f = fc * (1 + 50e-6)
    x = np.cos(2 * np.pi * f / common.Fs * np.arange(common.Fs))
    S = sigproc.extract_symbols(x, fc)
    S = np.array(list(S))
    print 1e6 * sigproc.drift(S) / (fc * common.Tsym)
    show.constellation(S, 'carrier')
    pylab.show()
