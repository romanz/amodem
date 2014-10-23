import numpy as np
import logging

log = logging.getLogger(__name__)

from . import common
from . import config
from . import wave

CALIBRATION_SYMBOLS = int(1.0 * config.Fs)
ALLOWED_EXCEPTIONS = (IOError, KeyboardInterrupt)


def send(wave_play=wave.play, verbose=False):
    t = np.arange(0, CALIBRATION_SYMBOLS) * config.Ts
    signal = [np.sin(2 * np.pi * f * t) for f in config.frequencies]
    signal = common.dumps(np.concatenate(signal))

    p = wave_play(stdin=wave.sp.PIPE)
    fd = p.stdin
    try:
        while True:
            fd.write(signal)
    except ALLOWED_EXCEPTIONS:
        pass
    finally:
        p.kill()


FRAME_LENGTH = 200 * config.Nsym


def recorder(process):
    t = np.arange(0, FRAME_LENGTH) * config.Ts
    scaling_factor = 0.5 * len(t)
    carriers = [np.exp(2j * np.pi * f * t) for f in config.frequencies]
    carriers = np.array(carriers) / scaling_factor

    frame_size = int(wave.bytes_per_sample * FRAME_LENGTH)
    fd = process.stdout

    states = [True]
    errors = ['weak', 'strong', 'noisy']
    try:
        while True:
            data = fd.read(frame_size)
            if len(data) < frame_size:
                return
            data = common.loads(data)
            frame = data - np.mean(data)

            coeffs = np.dot(carriers, frame)
            peak = np.max(np.abs(frame))
            total = np.sqrt(np.dot(frame, frame) / scaling_factor)

            max_index = np.argmax(np.abs(coeffs))
            freq = config.frequencies[max_index]
            rms = abs(coeffs[max_index])
            coherency = rms / total
            flags = [rms > 0.1, peak < 1.0, coherency > 0.9999]

            states.append(all(flags))
            states = states[-2:]

            message = 'good signal'
            error = not any(states)
            if error:
                error_index = flags.index(False)
                message = 'too {} signal'.format(errors[error_index])

            yield dict(
                freq=freq, rms=rms, peak=peak, coherency=coherency,
                total=total, error=error, message=message
            )
    except ALLOWED_EXCEPTIONS:
        pass
    finally:
        process.kill()

fmt = '{freq:6.0f} Hz: {message:s}{extra:s}'
fields = ['peak', 'total', 'rms', 'coherency']

def recv(wave_record=wave.record, verbose=False, output=None):
    extra = ''
    if verbose:
        extra = ''.join(', {0}={{{0}:.4f}}'.format(f) for f in fields)
    for r in recorder(wave_record(stdout=wave.sp.PIPE)):
        msg = fmt.format(extra=extra.format(**r), **r)
        if not r['error']:
            log.info(msg)
        else:
            log.error(msg)
