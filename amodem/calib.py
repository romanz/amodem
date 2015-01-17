import numpy as np
import itertools
import logging
import subprocess

log = logging.getLogger(__name__)

from . import common
from . import dsp
from . import sampling

ALLOWED_EXCEPTIONS = (IOError, KeyboardInterrupt)


def volume_controller(cmd):
    def controller(level):
        assert 0 < level <= 1
        percent = 100 * level
        args = '{0} {1:.0f}%'.format(cmd, percent)
        log.debug('Setting volume: %.3f%% (via "%s")', percent, args)
        subprocess.check_call(args=args, shell=True)
    return controller if cmd else (lambda level: None)


def send(config, dst, volume_cmd=None):
    volume_ctl = volume_controller(volume_cmd)
    volume_ctl(1.0)  # full scale output volume

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

    errors = ['weak', 'strong', 'noisy']
    try:
        for coeffs, peak, total in frame_iter(config, src, frame_length):
            max_index = np.argmax(coeffs)
            freq = config.frequencies[max_index]
            rms = abs(coeffs[max_index])
            coherency = rms / total
            flags = [total > 0.1, peak < 1.0, coherency > 0.99]

            success = all(flags)
            if success:
                message = 'good signal'
            else:
                message = 'too {0} signal'.format(errors[flags.index(False)])

            yield common.AttributeHolder(dict(
                freq=freq, rms=rms, peak=peak, coherency=coherency,
                total=total, success=success, message=message
            ))
    except ALLOWED_EXCEPTIONS:
        pass


def volume_calibration(result_iterator, volume_ctl):
    min_level = 0.01
    max_level = 1.0
    level = 0.5
    step = 0.25

    target_level = 0.4  # not too strong, not too weak
    iters_per_update = 10  # update every 2 seconds

    for index, result in enumerate(itertools.chain([None], result_iterator)):
        if index % iters_per_update == 0:
            if index > 0:  # skip dummy (first result)
                sign = 1 if (result.total < target_level) else -1
                level = level + step * sign
                level = min(max(level, min_level), max_level)
                step = step * 0.5

            volume_ctl(level)  # should run "before" first actual iteration

        if index > 0:  # skip dummy (first result)
            yield result


def recv(config, src, verbose=False, volume_cmd=None):
    fmt = '{0.freq:6.0f} Hz: {0.message:20s}'
    if verbose:
        fields = ['peak', 'total', 'rms', 'coherency']
        fmt += ', '.join('{0}={{0.{0}:.4f}}'.format(f) for f in fields)

    result_iterator = detector(config=config, src=src)
    volume_ctl = volume_controller(volume_cmd)

    for result in volume_calibration(result_iterator, volume_ctl):
        log.info(fmt.format(result))
