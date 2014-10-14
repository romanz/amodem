import numpy as np
import logging
import sys

log = logging.getLogger(__name__)

from . import common
from . import config
from . import wave

CALIBRATION_SYMBOLS = int(1.0 * config.Fs)
ALLOWED_EXCEPTIONS = (IOError, KeyboardInterrupt)


def send(wave_play=wave.play):
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


FRAME_LENGTH = 100 * config.Nsym


def recorder(process):
    frame_size = int(wave.bytes_per_sample * FRAME_LENGTH)
    fd = process.stdout
    try:
        while True:
            data = fd.read(frame_size)
            if len(data) < frame_size:
                return
            data = common.loads(data)
            data = data - np.mean(data)
            yield data
    except ALLOWED_EXCEPTIONS:
        pass
    finally:
        process.kill()


def recv(wave_record=wave.record, log=sys.stdout.write):
    t = np.arange(0, FRAME_LENGTH) * config.Ts
    carriers = [np.exp(2j * np.pi * f * t) for f in config.frequencies]
    carriers = np.array(carriers) / (0.5 * len(t))

    for frame in recorder(wave_record(stdout=wave.sp.PIPE)):
        peak = np.max(np.abs(frame))
        coeffs = np.dot(carriers, frame)
        max_index = np.argmax(np.abs(coeffs))
        max_coeff = coeffs[max_index]

        freq = config.frequencies[max_index]
        rms = abs(max_coeff)
        total = np.sqrt(np.dot(frame, frame) / (0.5 * len(t)))
        coherency = rms / total
        log(fmt.format(freq / 1e3, 100 * coherency, rms, total, peak))

fmt = '{:4.0f} kHz @ {:6.2f}% : RMS = {:.4f}, Total = {:.4f}, Peak = {:.4f}\n'
