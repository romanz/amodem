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
    def __init__(self, freq, Fs, filt, phase=0):
        self.freq = freq
        self.phase = phase
        self.Ts = 1.0/Fs
        self.filt = filt

    def handle(self, sample):
        self.pred = np.cos(self.phase)
        self.quad = np.cos(self.phase)
        err = self.quad * sample
        self.freq += self.filt(err)
        self.phase += self.freq * self.Ts


def test():
    pass
