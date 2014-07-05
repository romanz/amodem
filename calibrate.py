import numpy as np
import common
import sigproc
import wave
import pylab

Tsample = 1
t = np.arange(int(Tsample * common.Fs)) * common.Ts
sig = np.exp(2j * np.pi * common.Fc * t)
sig_dump = common.dumps(sig)

def send():
    p = wave.play('-', stdin=wave.sp.PIPE)
    while True:
        p.stdin.write(sig_dump)

def recv():
    out = wave.record('-', stdout=wave.sp.PIPE).stdout
    while True:
        data = out.read(len(sig_dump))
        _, x = common.loads(data)
        x = x - np.mean(x)

        c = np.abs(np.dot(x, sig)) / (np.sqrt(0.5 * len(x)) * sigproc.norm(x))
        z = np.dot(x, sig.conj()) / (0.5 * len(x))
        amp = np.abs(z)
        phase = np.angle(z)
        peak = np.max(np.abs(x))
        print('coherence={:.3f} amp={:.3f} phase={:.1f} peak={:.3f}'.format(c, amp, phase * 180 / np.pi, peak))

def plot(x, z):
    pylab.plot(x)
    pylab.plot((sig * z).real)
    pylab.show()

if __name__ == '__main__':
    import sys
    opt, = sys.argv[1:]
    if opt == 'send':
        send()
    if opt == 'recv':
        recv()

