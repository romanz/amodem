import numpy as np
import logging
import itertools
import time

log = logging.getLogger(__name__)

from . import train
from . import wave

from . import common
from . import config
from . import dsp
from . import stream
from . import framing
from . import equalizer

modem = dsp.MODEM(config)


class Writer(object):
    def __init__(self, fd):
        self.last_timestamp = time.time()
        self.offset = 0
        self.fd = fd

    def write(self, sym, n=1):
        sym = np.array(sym)
        data = common.dumps(sym, n)
        self.fd.write(data)
        self.offset += len(data)
        if time.time() > self.last_timestamp + 1:
            data_duration = self.offset / wave.bytes_per_second
            log.debug('%10.3f seconds of data audio sent', data_duration)
            self.last_timestamp += 1

    def start(self):
        carrier = modem.carriers[config.carrier_index]
        for value in train.prefix:
            self.write(carrier * value)

        silence = np.zeros(train.silence_length * config.Nsym)
        symbols = equalizer.train_symbols(train.equalizer_length)
        signal = equalizer.modulator(symbols)
        self.write(silence)
        self.write(signal)
        self.write(silence)

    def modulate(self, bits):
        padding = [0] * modem.bits_per_baud
        bits = itertools.chain(bits, padding)
        symbols_iter = modem.qam.encode(bits)
        carriers = modem.carriers / config.Nfreq
        for _, symbols in common.iterate(symbols_iter, size=config.Nfreq):
            symbols = np.array(list(symbols))
            self.write(np.dot(symbols, carriers))


def main(args):
    log.info('Running MODEM @ {:.1f} kbps'.format(modem.modem_bps / 1e3))

    writer = Writer(args.output)

    # pre-padding audio with silence
    writer.write(np.zeros(int(config.Fs * args.silence_start)))

    writer.start()

    training_size = writer.offset
    training_duration = training_size / wave.bytes_per_second
    log.info('%.3f seconds of training audio', training_duration)

    reader = stream.Reader(args.input, bufsize=(64 << 10), eof=True)
    data = list(itertools.chain.from_iterable(reader))
    bits = list(framing.encode(data))
    data_ = list(framing.decode(bits))
    writer.modulate(bits=bits)

    data_size = writer.offset - training_size
    log.info('%.3f seconds of data audio, for %.3f kB of data',
             data_size / wave.bytes_per_second, reader.total / 1e3)

    # post-padding audio with silence
    writer.write(np.zeros(int(config.Fs * args.silence_stop)))
