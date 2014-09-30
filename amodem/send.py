import numpy as np
import logging
import itertools

log = logging.getLogger(__name__)

from . import train
from . import wave

from . import common
from . import config
from . import stream
from . import framing
from . import equalizer
from . import dsp

modem = dsp.MODEM(config.symbols)


class Writer(object):
    def __init__(self, fd):
        self.offset = 0
        self.fd = fd

    def write(self, sym, n=1):
        sym = np.array(sym)
        data = common.dumps(sym, n)
        self.fd.write(data)
        self.offset += len(data)

    def start(self):
        carrier = config.carriers[config.carrier_index]
        for value in train.prefix:
            self.write(carrier * value)

        silence = np.zeros(train.silence_length * config.Nsym)
        symbols = equalizer.train_symbols(train.equalizer_length)
        signal = equalizer.modulator(symbols)
        self.write(silence)
        self.write(signal)
        self.write(silence)

    def modulate(self, bits):
        padding = [0] * config.bits_per_baud
        bits = itertools.chain(bits, padding)
        symbols_iter = modem.encode(bits)
        carriers = config.carriers / config.Nfreq
        for i, symbols in common.iterate(symbols_iter,
                                         size=config.Nfreq, enumerate=True):
            symbols = np.array(list(symbols))
            self.write(np.dot(symbols, carriers))

            data_duration = (i / config.Nfreq + 1) * config.Tsym
            if data_duration % 1 == 0:
                bits_size = data_duration * config.modem_bps
                log.debug('Sent %8.1f kB', bits_size / 8e3)


def main(args):
    writer = Writer(args.output)

    # pre-padding audio with silence
    writer.write(np.zeros(int(config.Fs * args.silence_start)))

    writer.start()

    training_size = writer.offset
    training_duration = training_size / wave.bytes_per_second
    log.info('Sending %.3f seconds of training audio', training_duration)

    reader = stream.Reader(args.input, bufsize=(64 << 10), eof=True)
    data = itertools.chain.from_iterable(reader)
    bits = framing.encode(data)
    log.info('Starting modulation: %s', modem)
    writer.modulate(bits=bits)

    data_size = writer.offset - training_size
    log.info('Sent %.3f kB @ %.3f seconds',
             reader.total / 1e3, data_size / wave.bytes_per_second)

    # post-padding audio with silence
    writer.write(np.zeros(int(config.Fs * args.silence_stop)))
