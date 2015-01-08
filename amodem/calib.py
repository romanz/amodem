import numpy as np
import itertools
import logging

log = logging.getLogger(__name__)

from . import common

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


def frame_iter(config, src):
    frame_length = 200 * config.Nsym
    frame_size = frame_length * config.sample_size

    t = np.arange(0, frame_length) * config.Ts

    scaling_factor = 0.5 * len(t)
    carriers = [np.exp(2j * np.pi * f * t) for f in config.frequencies]
    carriers = np.array(carriers) / scaling_factor

    while True:
        data = src.read(frame_size)
        if len(data) < frame_size:
            return
        data = common.loads(data)
        frame = data - np.mean(data)

        coeffs = np.dot(carriers, frame)
        peak = np.max(np.abs(frame))
        total = np.sqrt(np.dot(frame, frame) / scaling_factor)
        yield coeffs, peak, total


def detector(config, src):

    states = [True]
    errors = ['weak', 'strong', 'noisy']
    try:
        for coeffs, peak, total in frame_iter(config, src):
            max_index = np.argmax(np.abs(coeffs))
            freq = config.frequencies[max_index]
            rms = abs(coeffs[max_index])
            coherency = rms / total
            flags = [rms > 0.1, peak < 1.0, coherency > 0.99]

            states.append(all(flags))
            states = states[-2:]

            message = 'good signal'
            error = not any(states)
            if error:
                error_index = flags.index(False)
                message = 'too {0} signal'.format(errors[error_index])

            yield dict(
                freq=freq, rms=rms, peak=peak, coherency=coherency,
                total=total, error=error, message=message
            )
    except ALLOWED_EXCEPTIONS:
        pass

fmt = '{freq:6.0f} Hz: {message:s}{extra:s}'
fields = ['peak', 'total', 'rms', 'coherency']


# pylint: disable=star-args
def recv(config, src, verbose=False):
    extra = ''
    if verbose:
        extra = ''.join(', {0}={{{0}:.4f}}'.format(f) for f in fields)

    for result in detector(config=config, src=src):
        msg = fmt.format(extra=extra.format(**result), **result)
        if not result['error']:
            log.info(msg)
        else:
            log.error(msg)
