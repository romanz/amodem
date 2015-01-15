import numpy as np
import logging
import itertools

log = logging.getLogger(__name__)

from . import common
from . import stream
from . import framing
from . import equalizer
from . import dsp


class Sender(object):
    def __init__(self, fd, config):
        self.offset = 0
        self.fd = fd
        self.modem = dsp.MODEM(config.symbols)
        self.carriers = config.carriers / config.Nfreq
        self.pilot = config.carriers[config.carrier_index]
        self.silence = np.zeros(equalizer.silence_length * config.Nsym)
        self.iters_per_report = config.baud  # report once per second
        self.padding = [0] * config.bits_per_baud
        self.equalizer = equalizer.Equalizer(config)

    def write(self, sym):
        sym = np.array(sym)
        data = common.dumps(sym)
        self.fd.write(data)
        self.offset += len(sym)

    def start(self):
        for value in equalizer.prefix:
            self.write(self.pilot * value)

        symbols = self.equalizer.train_symbols(equalizer.equalizer_length)
        signal = self.equalizer.modulator(symbols)
        self.write(self.silence)
        self.write(signal)
        self.write(self.silence)

    def modulate(self, bits):
        bits = itertools.chain(bits, self.padding)
        Nfreq = len(self.carriers)
        symbols_iter = common.iterate(self.modem.encode(bits), size=Nfreq)
        for i, symbols in enumerate(symbols_iter, 1):
            self.write(np.dot(symbols, self.carriers))
            if i % self.iters_per_report == 0:
                total_bits = i * Nfreq * self.modem.bits_per_symbol
                log.debug('Sent %10.3f kB', total_bits / 8e3)


def main(config, src, dst):
    sender = Sender(dst, config=config)
    Fs = config.Fs

    # pre-padding audio with silence
    sender.write(np.zeros(int(Fs * config.silence_start)))

    sender.start()

    training_duration = sender.offset
    log.info('Sending %.3f seconds of training audio', training_duration / Fs)

    reader = stream.Reader(src, eof=True)
    data = itertools.chain.from_iterable(reader)
    bits = framing.encode(data)
    log.info('Starting modulation')
    sender.modulate(bits=bits)

    data_duration = sender.offset - training_duration
    log.info('Sent %.3f kB @ %.3f seconds',
             reader.total / 1e3, data_duration / Fs)

    # post-padding audio with silence
    sender.write(np.zeros(int(Fs * config.silence_stop)))
    return True
