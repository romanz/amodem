import numpy as np

def lfilter(b, a, x):
    b = np.array(b) / a[0]
    a = np.array(a[1:]) / a[0]

    x_ = [0] * len(b)
    y_ = [0] * len(a)
    for v in x:
        x_ = [v] + x_[:-1]
        u  = np.dot(x_, b)
        u = u - np.dot(y_, a)

        y_ = [u] + y_[1:]
        yield u

class QPSK(object):
    def __init__(self, bits_per_symbol):
        self._enc = {tuple(): 0.0} # End-Of-Stream symbol
        index = 0
        amps = [0.6, 1.0]
        N = (2 ** bits_per_symbol) / len(amps)
        for a in amps:
            for i in range(N):
                k = tuple(int(index & (1 << j) != 0) for j in range(bits_per_symbol))
                v = np.exp(2j * i * np.pi / N)
                self._enc[k] = v * a
                index += 1
        self._dec = {v: k for k, v in self._enc.items()}
        self.bits_per_symbol = bits_per_symbol

    def encode(self, bits):
        assert len(bits) % self.bits_per_symbol == 0
        for i in range(0, len(bits), self.bits_per_symbol):
            s = self._enc[ tuple(bits[i:i+self.bits_per_symbol]) ]
            yield s

    def decode(self, symbols):
        keys = np.array(self._dec.keys())
        for s in symbols:
            index = np.argmin(np.abs(s - keys))
            bits = self._dec[ keys[index] ]
            for b in bits:
                yield b


qpsk = QPSK(bits_per_symbol=4)

def test_qpsk():
    q = QPSK(bits_per_symbol=2)
    bits = [1,1, 0,1, 0,0, 1,0]
    S = qpsk.encode(bits)
    assert list(qpsk.decode(list(S))) == bits
