import numpy as np
import logging
import itertools
import collections

log = logging.getLogger(__name__)

from . import dsp
from . import train
from . import common


class Detector(object):

    COHERENCE_THRESHOLD = 0.9

    CARRIER_DURATION = sum(train.prefix)
    CARRIER_THRESHOLD = int(0.9 * CARRIER_DURATION)
    SEARCH_WINDOW = int(0.1 * CARRIER_DURATION)

    TIMEOUT = 10.0  # [seconds]

    def __init__(self, config):
        self.freq = config.Fc
        self.omega = 2 * np.pi * self.freq / config.Fs
        self.Nsym = config.Nsym
        self.Tsym = config.Tsym
        self.maxlen = config.baud  # 1 second of symbols
        self.max_offset = self.TIMEOUT * config.Fs

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
        Zc = np.dot(Hc, x) / (0.5*len(x))
        amplitude = abs(Zc)
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
        offset = self.find_start(buf, self.CARRIER_DURATION*self.Nsym)
        start_time += (offset / self.Nsym - self.SEARCH_WINDOW) * self.Tsym
        log.debug('Carrier starts at %.3f ms', start_time * 1e3)

        return itertools.chain(buf[offset:], samples), amplitude

    def find_start(self, buf, length):
        N = len(buf)
        carrier = dsp.exp_iwt(self.omega, N)
        z = np.cumsum(buf * carrier)
        z = np.concatenate([[0], z])
        correlations = np.abs(z[length:] - z[:-length])
        return np.argmax(correlations)
