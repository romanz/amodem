"""Signal detection capabilities for amodem."""

import collections
import itertools
import logging
import threading

import numpy as np

from . import dsp
from . import equalizer
from . import common

log = logging.getLogger(__name__)


class Detector:

    COHERENCE_THRESHOLD = 0.9

    CARRIER_DURATION = sum(equalizer.prefix)
    CARRIER_THRESHOLD = int(0.9 * CARRIER_DURATION)
    SEARCH_WINDOW = int(0.1 * CARRIER_DURATION)
    START_PATTERN_LENGTH = SEARCH_WINDOW // 4

    def __init__(self, config, pylab):
        self.freq = config.Fc
        self.omega = 2 * np.pi * self.freq / config.Fs
        self.Nsym = config.Nsym
        self.Tsym = config.Tsym
        self.maxlen = config.baud  # 1 second of symbols
        self.max_offset = config.timeout * config.Fs
        self.plt = pylab

    def _wait(self, samples, stop_event: threading.Event = None):
        counter = 0
        bufs = collections.deque([], maxlen=self.maxlen)
        for offset, buf in common.iterate(samples, self.Nsym, index=True):
            if stop_event is not None and stop_event.is_set():
                raise StopIteration('Detector stop iteration by stop_event')
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

    def run(self, samples, stop_event: threading.Event = None):
        offset, bufs = self._wait(samples, stop_event=stop_event)

        length = (self.CARRIER_THRESHOLD - 1) * self.Nsym
        begin = offset - length

        start_time = begin * self.Tsym / self.Nsym
        log.info('Carrier detected at ~%.1f ms @ %.1f kHz',
                 start_time * 1e3, self.freq / 1e3)

        log.debug('Buffered %d ms of audio', len(bufs))

        bufs = list(bufs)[-self.CARRIER_THRESHOLD-self.SEARCH_WINDOW:]
        n = self.SEARCH_WINDOW + self.CARRIER_DURATION - self.CARRIER_THRESHOLD
        trailing = list(itertools.islice(samples, n * self.Nsym))
        bufs.append(np.array(trailing))

        buf = np.concatenate(bufs)
        offset = self.find_start(buf)
        start_time += (offset / self.Nsym - self.SEARCH_WINDOW) * self.Tsym
        log.debug('Carrier starts at %.3f ms', start_time * 1e3)

        buf = buf[offset:]

        prefix_length = self.CARRIER_DURATION * self.Nsym
        amplitude, freq_err = self.estimate(buf[:prefix_length])
        return itertools.chain(buf, samples), amplitude, freq_err

    def find_start(self, buf):
        carrier = dsp.exp_iwt(self.omega, self.Nsym)
        carrier = np.tile(carrier, self.START_PATTERN_LENGTH)
        zeroes = carrier * 0.0
        signal = np.concatenate([zeroes, carrier])
        signal = (2 ** 0.5) * signal / dsp.norm(signal)

        corr = np.abs(np.correlate(buf, signal))
        norm_b = np.sqrt(np.correlate(np.abs(buf)**2, np.ones(len(signal))))
        coeffs = np.zeros_like(corr)
        coeffs[norm_b > 0.0] = corr[norm_b > 0.0] / norm_b[norm_b > 0.0]

        index = np.argmax(coeffs)
        log.info('Carrier coherence: %.3f%%', coeffs[index] * 100)
        offset = index + len(zeroes)
        return offset

    def estimate(self, buf, skip=5):
        filt = dsp.exp_iwt(-self.omega, self.Nsym) / (0.5 * self.Nsym)
        frames = common.iterate(buf, self.Nsym)
        symbols = [np.dot(filt, frame) for frame in frames]
        symbols = np.array(symbols[skip:-skip])

        amplitude = np.mean(np.abs(symbols))
        log.info('Carrier symbols amplitude : %.3f', amplitude)

        phase = np.unwrap(np.angle(symbols)) / (2 * np.pi)
        indices = np.arange(len(phase))
        a, b = dsp.linear_regression(indices, phase)
        self.plt.figure()
        self.plt.plot(indices, phase, ':')
        self.plt.plot(indices, a * indices + b)

        freq_err = a / (self.Tsym * self.freq)
        log.info('Frequency error: %.3f ppm', freq_err * 1e6)
        self.plt.title(f'Frequency drift: {freq_err * 1e6:.3f} ppm')
        return amplitude, freq_err
