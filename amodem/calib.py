import numpy as np
import itertools
import logging

log = logging.getLogger(__name__)

from . import common
from . import dsp
from . import sampling

ALLOWED_EXCEPTIONS = (IOError, KeyboardInterrupt)


def send(config, dst):
    calibration_symbols = int(1.0 * config.Fs)
    t = np.arange(0, calibration_symbols) * config.Ts
    signals = [np.sin(2 * np.pi * f * t) for f in config.frequencies]
    signals = [common.dumps(s) for s in signals]

    try:
        for signal in itertools.cycle(signals):
            dst.write(signal)
    except ALLOWED_EXCEPTIONS:
        pass


def frame_iter(config, src, frame_length):
    frame_size = frame_length * config.Nsym * config.sample_size
    omegas = 2 * np.pi * config.frequencies / config.Fs

    while True:
        data = src.read(frame_size)
        if len(data) < frame_size:
            return
        data = common.loads(data)
        frame = data - np.mean(data)

        sampler = sampling.Sampler(frame)
        symbols = dsp.Demux(sampler, omegas, config.Nsym)

        symbols = np.array(list(symbols))
        coeffs = np.mean(np.abs(symbols) ** 2, axis=0) ** 0.5

        peak = np.max(np.abs(frame))
        total = np.sqrt(np.dot(frame, frame) / (0.5 * len(frame)))
        yield coeffs, peak, total


def detector(config, src, frame_length=200):

    states = [True]
    errors = ['weak', 'strong', 'noisy']
    try:
        for coeffs, peak, total in frame_iter(config, src, frame_length):
            max_index = np.argmax(coeffs)
            freq = config.frequencies[max_index]
            rms = abs(coeffs[max_index])
            coherency = rms / total
            flags = [rms > 0.1, peak < 1.0, coherency > 0.99]

            states.append(all(flags))
            states = states[-2:]

            message = 'good signal'
            error = not any(states)
            if error:
                message = 'too {0} signal'.format(errors[flags.index(False)])

            yield common.AttributeHolder(dict(
                freq=freq, rms=rms, peak=peak, coherency=coherency,
                total=total, error=error, message=message
            ))
    except ALLOWED_EXCEPTIONS:
        pass


def recv(config, src, verbose=False):
    fmt = '{0.freq:6.0f} Hz: {0.message:s}'
    if verbose:
        fields = ['peak', 'total', 'rms', 'coherency']
        fmt += ''.join(', {0}={{0.{0}:.4f}}'.format(f) for f in fields)

    for result in detector(config=config, src=src):
        msg = fmt.format(result)
        if not result.error:
            log.info(msg)
        else:
            log.error(msg)
