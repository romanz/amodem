import numpy as np

class Loop(object):
    def __init__(self, Kp, Ki, Fs, output=0):
        Ts = 1.0 / Fs
        self.coeffs = [Ki*Ts/2 - Kp, Ki*Ts/2 + Kp]
        self.output = output
        self.inputs = [0]

    def handle(self, err):
        self.inputs.append(err)
        self.output = self.output + np.dot(self.inputs, self.coeffs)
        self.inputs.pop(0)
        return self.output


class PLL(object):
    def __init__(self, freq, Fs, phase=0, Kerr=1, Kphase=0.04):
        self.freq = freq
        self.phase = phase
        self.Ts = 1.0/Fs
        self.Kphase = Kphase
        self.Kerr = Kerr

    def handle(self, sample):
        self.pred = np.cos(self.phase)
        self.quad = np.sin(self.phase)
        self.err = self.quad * (self.pred - sample)
        self.filtered_err = self.Kerr * self.err
        self.freq += self.filtered_err
        self.phase += self.Kphase * self.filtered_err
        self.phase += 2 * np.pi * self.freq * self.Ts

def test():
    f = 1.2345678e3
    Fs = 32e3
    Nsym = 32

    df = f * 10e-3
    f_ = f + df

    t = np.arange(100*Nsym) / Fs

    pll = PLL(f, Fs)
    x = -1.0 * np.cos( 2 * np.pi * f_ * t)

    y = []
    for s in x:
        pll.handle(s)
        y.append([pll.err, pll.filtered_err, pll.freq - f, df])

    print y[-1]
    import pylab
    pylab.plot(y)
    pylab.show()
