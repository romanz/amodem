#!/usr/bin/env python
import numpy as np
import common
import sigproc
import wave

Tsample = 1
t = np.arange(int(Tsample * common.Fs)) * common.Ts
sig = np.exp(2j * np.pi * common.Fc * t)
sig_dump = common.dumps(sig)


def send():
    p = wave.play('-', stdin=wave.sp.PIPE)
    while True:
        try:
            p.stdin.write(sig_dump)
        except IOError:
            return


def recv():
    out = wave.record('-', stdout=wave.sp.PIPE).stdout
    while True:
        data = out.read(len(sig_dump))
        if len(data) < len(sig_dump):
            return
        try:
            x = common.loads(data)
        except common.SaturationError as e:
            print('saturation: {}'.format(e))
            continue
        x = x - np.mean(x)

        c = np.abs(np.dot(x, sig)) / (np.sqrt(0.5 * len(x)) * sigproc.norm(x))
        z = np.dot(x, sig.conj()) / (0.5 * len(x))
        amp = np.abs(z)
        phase = np.angle(z)
        peak = np.max(np.abs(x))
        print('coherence={:.3f} amp={:.3f} phase={:.1f} peak={:.3f}'.format(
              c, amp, phase * 180 / np.pi, peak))


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    sub = p.add_subparsers()
    sub.add_parser('send').set_defaults(func=send)
    sub.add_parser('recv').set_defaults(func=recv)
    args = p.parse_args()
    try:
        args.func()
    except KeyboardInterrupt:
        pass
