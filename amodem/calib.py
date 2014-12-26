import numpy as np
import logging

log = logging.getLogger(__name__)

from subprocess import PIPE
from . import common
from . import audio

ALLOWED_EXCEPTIONS = (IOError, KeyboardInterrupt)


def send(config, audio_play=audio.play, verbose=False):
    calibration_symbols = int(1.0 * config.Fs)
    t = np.arange(0, calibration_symbols) * config.Ts
    signal = [np.sin(2 * np.pi * f * t) for f in config.frequencies]
    signal = common.dumps(np.concatenate(signal))

    player = audio_play(Fs=config.Fs)
    p = player.launch(stdin=PIPE)
    fd = p.stdin
    try:
        while True:
            fd.write(signal)
    except ALLOWED_EXCEPTIONS:
        pass
    finally:
        p.kill()


def run_recorder(config, recorder):

    FRAME_LENGTH = 200 * config.Nsym
    process = recorder.launch(stdout=PIPE)
    frame_size = int(recorder.bytes_per_sample * FRAME_LENGTH)

    t = np.arange(0, FRAME_LENGTH) * config.Ts
    scaling_factor = 0.5 * len(t)
    carriers = [np.exp(2j * np.pi * f * t) for f in config.frequencies]
    carriers = np.array(carriers) / scaling_factor

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
    finally:
        process.kill()

fmt = '{freq:6.0f} Hz: {message:s}{extra:s}'
fields = ['peak', 'total', 'rms', 'coherency']

def recv(config, audio_record=audio.record, verbose=False):
    extra = ''
    if verbose:
        extra = ''.join(', {0}={{{0}:.4f}}'.format(f) for f in fields)

    recorder = audio_record(Fs=config.Fs)
    for result in run_recorder(config=config, recorder=recorder):
        msg = fmt.format(extra=extra.format(**result), **result)
        if not result['error']:
            log.info(msg)
        else:
            log.error(msg)
