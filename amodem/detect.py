import numpy as np
import logging
import itertools
import collections

log = logging.getLogger(__name__)

from . import dsp
from . import equalizer
from . import common


class Detector(object):

    COHERENCE_THRESHOLD = 0.9

    CARRIER_DURATION = sum(equalizer.prefix)
    CARRIER_THRESHOLD = int(0.9 * CARRIER_DURATION)
    SEARCH_WINDOW = int(0.1 * CARRIER_DURATION)

    TIMEOUT = 10.0  # [seconds]

    def __init__(self, config, pylab):
        self.freq = config.Fc
        self.omega = 2 * np.pi * self.freq / config.Fs
        self.Nsym = config.Nsym
        self.Tsym = config.Tsym
        self.maxlen = config.baud  # 1 second of symbols
        self.max_offset = self.TIMEOUT * config.Fs
        self.plt = pylab

    def _wait(self, samples):
        counter = 0
        bufs = collections.deque([], maxlen=self.maxlen)
        for offset, buf in common.iterate(samples, self.Nsym, index=True):
            if offset > self.max_offset:
                raise ValueError('Timeout waiting for carrier')
            bufs.append(buf)

            coeff = dsp.coherence(buf, self.omega)
            if abs(coeff) > self.COHERENCE_THRESHOLD:
                counter += 1
            else:
                counter = 0

            if counter == self.CARRIER_THRESHOLD:
                return offset, bufs

        raise ValueError('No carrier detected')

    def run(self, samples):
        offset, bufs = self._wait(samples)

        length = (self.CARRIER_THRESHOLD - 1) * self.Nsym
        begin = offset - length

        x = np.concatenate(tuple(bufs)[-self.CARRIER_THRESHOLD:-1])
        Hc = dsp.exp_iwt(-self.omega, len(x))
        amplitude = np.abs(np.dot(Hc, x) / (0.5 * len(x)))
        start_time = begin * self.Tsym / self.Nsym
        log.info('Carrier detected at ~%.1f ms @ %.1f kHz:'
                 ' coherence=%.3f%%, amplitude=%.3f',
                 start_time * 1e3, self.freq / 1e3,
                 np.abs(dsp.coherence(x, self.omega)) * 100, amplitude)

        log.debug('Buffered %d ms of audio', len(bufs))

        bufs = list(bufs)[-self.CARRIER_THRESHOLD-self.SEARCH_WINDOW:]
        n = self.SEARCH_WINDOW + self.CARRIER_DURATION - self.CARRIER_THRESHOLD
        trailing = list(itertools.islice(samples, n * self.Nsym))
        bufs.append(np.array(trailing))

        buf = np.concatenate(bufs)
        offset = self.find_start(buf, duration=self.CARRIER_DURATION)
        start_time += (offset / self.Nsym - self.SEARCH_WINDOW) * self.Tsym
        log.debug('Carrier starts at %.3f ms', start_time * 1e3)

        buf = buf[offset:]

        prefix_length = self.CARRIER_DURATION * self.Nsym
        amplitude, freq_err = self.estimate(buf[:prefix_length])
        return itertools.chain(buf, samples), amplitude, freq_err

    def find_start(self, buf, duration):
        filt = dsp.FIR(dsp.exp_iwt(self.omega, self.Nsym))
        p = np.abs(list(filt(buf))) ** 2
        p = np.cumsum(p)[self.Nsym-1:]
        p = np.concatenate([[0], p])
        length = (duration - 1) * self.Nsym
        correlations = np.abs(p[length:] - p[:-length])
        offset = np.argmax(correlations)
        return offset

    def estimate(self, buf, skip=5):
        filt = dsp.exp_iwt(-self.omega, self.Nsym) / (0.5 * self.Nsym)
        frames = common.iterate(buf, self.Nsym)
        symbols = [np.dot(filt, frame) for frame in frames]
        symbols = np.array(symbols[skip:-skip])

        amplitude = np.mean(np.abs(symbols))
        log.debug('Carrier symbols amplitude : %.3f', amplitude)

        phase = np.unwrap(np.angle(symbols)) / (2 * np.pi)
        indices = np.arange(len(phase))
        a, b = dsp.linear_regression(indices, phase)
        self.plt.figure()
        self.plt.plot(indices, phase, ':')
        self.plt.plot(indices, a * indices + b)

        freq_err = a / (self.Tsym * self.freq)
        last_phase = a * indices[-1] + b
        log.debug('Current phase on carrier: %.3f', last_phase)
        log.debug('Frequency error: %.2f ppm', freq_err * 1e6)
        self.plt.title('Frequency drift: {0:.3f} ppm'.format(freq_err * 1e6))

        return amplitude, freq_err
