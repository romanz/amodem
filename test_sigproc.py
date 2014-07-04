import sigproc
import itertools

def test_qam():
    q = sigproc.QAM(bits_per_symbol=8, radii=[0.25, 0.5, 0.75, 1.0])
    bits = [(1,1,0,1,0,0,1,0), (0,1,0,0,0,1,1,1)]
    stream = itertools.chain(*bits)
    S = q.encode(list(stream))
    decoded = list(q.decode(list(S)))
    assert decoded == bits
