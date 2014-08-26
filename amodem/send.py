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
from . import ecc
from . import equalizer

modem = dsp.MODEM(config)


class Writer(object):
    def __init__(self):
        self.last = time.time()
        self.offset = 0

    def write(self, fd, sym, n=1):
        sym = np.array(sym)
        data = common.dumps(sym, n)
        fd.write(data)
        self.offset += len(data)
        if time.time() > self.last + 1:
            log.debug('%10.3f seconds of data audio',
                      self.offset / wave.bytes_per_second)
            self.last += 1

writer = Writer()


def start(fd, c):
    for value in train.prefix:
        writer.write(fd, c * value)

    silence = [0] * (train.silence_length * config.Nsym)
    writer.write(fd, silence)
    symbols = equalizer.train_symbols(train.equalizer_length)
    signal = equalizer.modulator(symbols)
    writer.write(fd, signal)
    writer.write(fd, silence)


def modulate(fd, bits):
    symbols_iter = modem.qam.encode(bits)
    symbols_iter = itertools.chain(symbols_iter, itertools.repeat(0))
    carriers = modem.carriers / config.Nfreq
    while True:
        symbols = itertools.islice(symbols_iter, config.Nfreq)
        symbols = np.array(list(symbols))
        writer.write(fd, np.dot(symbols, carriers))
        if all(symbols == 0):  # EOF marker
            break


def main(args):
    log.info('Running MODEM @ {:.1f} kbps'.format(modem.modem_bps / 1e3))

    # padding audio with silence
    writer.write(args.output, np.zeros(int(config.Fs * args.silence_start)))

    start(args.output, modem.carriers[config.carrier_index])

    training_size = writer.offset
    log.info('%.3f seconds of training audio',
             training_size / wave.bytes_per_second)

    reader = stream.Reader(args.input, bufsize=(64 << 10), eof=True)
    data = itertools.chain.from_iterable(reader)
    encoded = itertools.chain.from_iterable(ecc.encode(data))
    modulate(args.output, bits=common.to_bits(encoded))

    data_size = writer.offset - training_size
    log.info('%.3f seconds of data audio, for %.3f kB of data',
             data_size / wave.bytes_per_second, reader.total / 1e3)

    # padding audio with silence
    writer.write(args.output, np.zeros(int(config.Fs * args.silence_stop)))
