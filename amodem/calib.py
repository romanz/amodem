#!/usr/bin/env python
import numpy as np

from . import common
from . import config
from . import sigproc
from . import wave

Tsample = 1
t = np.arange(int(Tsample * config.Fs)) * config.Ts
sig = np.exp(2j * np.pi * config.Fc * t)
sig_dump = common.dumps(sig)


def send(wave_play=wave.play):
    p = wave_play('-', stdin=wave.sp.PIPE, stderr=open('/dev/null'))
    try:
        while True:
            try:
                p.stdin.write(sig_dump)
            except IOError:
                return
    except KeyboardInterrupt:
        p.kill()


def recv(wave_record=wave.record):
    p = wave_record('-', stdout=wave.sp.PIPE)
    try:
        while True:
            data = p.stdout.read(len(sig_dump))
            if len(data) < len(sig_dump):
                return
            try:
                x = common.loads(data)
            except common.SaturationError as e:
                print('saturation: {}'.format(e))
                continue
            x = x - np.mean(x)

            normalization_factor = np.sqrt(0.5 * len(x)) * sigproc.norm(x)
            coherence = np.abs(np.dot(x, sig)) / normalization_factor
            z = np.dot(x, sig.conj()) / (0.5 * len(x))
            amplitude = np.abs(z)
            phase = np.angle(z)
            peak = np.max(np.abs(x))

            fmt = 'coherence={:.3f} amplitude={:.3f} phase={:+.1f} peak={:.3f}'
            print(fmt.format(coherence, amplitude, phase * 180 / np.pi, peak))
    except KeyboardInterrupt:
        p.kill()

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
