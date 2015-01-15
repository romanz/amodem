import numpy as np
import logging
import itertools
import functools
import time

log = logging.getLogger(__name__)

from . import stream
from . import dsp
from . import sampling
from . import common
from . import framing
from . import equalizer
from . import detect


class Receiver(object):

    def __init__(self, config, pylab=None):
        self.stats = {}
        self.plt = pylab
        self.modem = dsp.MODEM(config.symbols)
        self.frequencies = np.array(config.frequencies)
        self.omegas = 2 * np.pi * self.frequencies / config.Fs
        self.Nsym = config.Nsym
        self.Tsym = config.Tsym
        self.iters_per_update = 100  # [ms]
        self.modem_bitrate = config.modem_bps
        self.equalizer = equalizer.Equalizer(config)
        self.carrier_index = config.carrier_index
        self.output_size = 0  # number of bytes written to output stream

    def _prefix(self, symbols, gain=1.0):
        S = common.take(symbols, len(equalizer.prefix))
        S = S[:, self.carrier_index] * gain
        sliced = np.round(np.abs(S))
        self.plt.figure()
        self.plt.subplot(121)
        self._constellation(S, sliced, 'Prefix')

        bits = np.array(sliced, dtype=int)
        self.plt.subplot(122)
        self.plt.plot(np.abs(S))
        self.plt.plot(equalizer.prefix)
        if any(bits != equalizer.prefix):
            raise ValueError('Incorrect prefix')
        log.debug('Prefix OK')

    def _train(self, sampler, order, lookahead):
        Nfreq = len(self.frequencies)
        equalizer_length = equalizer.equalizer_length
        train_symbols = self.equalizer.train_symbols(equalizer_length)
        train_signal = self.equalizer.modulator(train_symbols) * Nfreq

        prefix = postfix = equalizer.silence_length * self.Nsym
        signal_length = equalizer_length * self.Nsym + prefix + postfix

        signal = sampler.take(signal_length + lookahead)

        coeffs = equalizer.train(
            signal=signal[prefix:-postfix],
            expected=train_signal,
            order=order, lookahead=lookahead
        )

        self.plt.figure()
        self.plt.plot(np.arange(order+lookahead), coeffs)

        equalization_filter = dsp.FIR(h=coeffs)
        equalized = list(equalization_filter(signal))
        equalized = equalized[prefix+lookahead:-postfix+lookahead]
        self._verify_training(equalized, train_symbols)
        return equalization_filter

    def _verify_training(self, equalized, train_symbols):
        equalizer_length = equalizer.equalizer_length
        symbols = self.equalizer.demodulator(equalized, equalizer_length)
        sliced = np.array(symbols).round()
        errors = np.array(sliced - train_symbols, dtype=np.bool)
        error_rate = errors.sum() / errors.size

        errors = np.array(symbols - train_symbols)
        rms = lambda x: (np.mean(np.abs(x) ** 2, axis=0) ** 0.5)

        noise_rms = rms(errors)
        signal_rms = rms(train_symbols)
        SNRs = 20.0 * np.log10(signal_rms / noise_rms)

        self.plt.figure()
        for (i, freq), snr in zip(enumerate(self.frequencies), SNRs):
            log.debug('%5.1f kHz: SNR = %5.2f dB', freq / 1e3, snr)
            self._constellation(symbols[:, i], train_symbols[:, i],
                                '$F_c = {0} Hz$'.format(freq), index=i)
        assert error_rate == 0, error_rate

    def _demodulate(self, sampler, symbols):
        streams = []
        symbol_list = []
        errors = {}

        def error_handler(received, decoded, freq):
            errors.setdefault(freq, []).append(received / decoded)

        generators = common.split(symbols, n=len(self.omegas))
        for freq, S in zip(self.frequencies, generators):
            equalized = []
            S = common.icapture(S, result=equalized)
            symbol_list.append(equalized)

            freq_handler = functools.partial(error_handler, freq=freq)
            bits = self.modem.decode(S, freq_handler)  # list of bit tuples
            streams.append(bits)  # stream per frequency

        self.stats['symbol_list'] = symbol_list
        self.stats['rx_bits'] = 0
        self.stats['rx_start'] = time.time()

        log.info('Starting demodulation')
        for i, block in enumerate(common.izip(streams), 1):
            for bits in block:
                self.stats['rx_bits'] = self.stats['rx_bits'] + len(bits)
                yield bits

            if i % self.iters_per_update == 0:
                self._update_sampler(i, errors, sampler)

    def _update_sampler(self, iter_index, errors, sampler):
        err = np.array([e for v in errors.values() for e in v])
        err = np.mean(np.angle(err))/(2*np.pi) if len(err) else 0
        errors.clear()

        duration = time.time() - self.stats['rx_start']
        sampler.freq -= 0.01 * err * self.Tsym
        sampler.offset -= err
        log.debug(
            'Got  %10.3f kB, realtime: %6.2f%%, drift: %+5.2f ppm',
            self.stats['rx_bits'] / 8e3,
            duration * 100.0 / (iter_index * self.Tsym),
            (1.0 - sampler.freq) * 1e6
        )

    def run(self, sampler, gain, output):
        symbols = dsp.Demux(sampler, omegas=self.omegas, Nsym=self.Nsym)
        self._prefix(symbols, gain=gain)

        filt = self._train(sampler, order=20, lookahead=20)
        sampler.equalizer = lambda x: list(filt(x))

        bitstream = self._demodulate(sampler, symbols)
        bitstream = itertools.chain.from_iterable(bitstream)

        data = framing.decode(bitstream)
        for chunk in common.iterate(data=data, size=256,
                                    truncate=False, func=bytearray):
            output.write(chunk)
            self.output_size += len(chunk)

    def report(self):
        if self.stats:
            duration = time.time() - self.stats['rx_start']
            audio_time = self.stats['rx_bits'] / float(self.modem_bitrate)
            log.debug('Demodulated %.3f kB @ %.3f seconds (%.1f%% realtime)',
                      self.stats['rx_bits'] / 8e3, duration,
                      100 * duration / audio_time if audio_time else 0)

            log.info('Received %.3f kB @ %.3f seconds = %.3f kB/s',
                     self.output_size * 1e-3, duration,
                     self.output_size * 1e-3 / duration)

            self.plt.figure()
            symbol_list = np.array(self.stats['symbol_list'])
            for i, freq in enumerate(self.frequencies):
                self._constellation(symbol_list[i], self.modem.symbols,
                                    '$F_c = {0} Hz$'.format(freq), index=i)
        self.plt.show()

    def _constellation(self, y, symbols, title, index=None):
        if index is not None:
            Nfreq = len(self.frequencies)
            height = np.floor(np.sqrt(Nfreq))
            width = np.ceil(Nfreq / float(height))
            self.plt.subplot(height, width, index + 1)

        theta = np.linspace(0, 2*np.pi, 1000)
        y = np.array(y)
        self.plt.plot(y.real, y.imag, '.')
        self.plt.plot(np.cos(theta), np.sin(theta), ':')
        points = np.array(symbols)
        self.plt.plot(points.real, points.imag, '+')
        self.plt.grid('on')
        self.plt.axis('equal')
        self.plt.axis(np.array([-1, 1, -1, 1])*1.1)
        self.plt.title(title)


class Dumper(object):
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst

    def read(self, size):
        data = self.src.read(size)
        self.dst.write(data)
        return data


def main(config, src, dst, dump_audio=None, pylab=None):
    if dump_audio:
        src = Dumper(src, dump_audio)
    reader = stream.Reader(src, data_type=common.loads)
    signal = itertools.chain.from_iterable(reader)

    log.debug('Skipping %.3f seconds', config.skip_start)
    common.take(signal, int(config.skip_start * config.Fs))

    pylab = pylab or common.Dummy()
    detector = detect.Detector(config=config, pylab=pylab)
    receiver = Receiver(config=config, pylab=pylab)
    try:
        log.info('Waiting for carrier tone: %.1f kHz', config.Fc / 1e3)
        signal, amplitude, freq_error = detector.run(signal)

        freq = 1 / (1.0 + freq_error)  # receiver's compensated frequency
        log.debug('Frequency correction: %.3f ppm', (freq - 1) * 1e6)

        gain = 1.0 / amplitude
        log.debug('Gain correction: %.3f', gain)

        sampler = sampling.Sampler(signal, sampling.Interpolator(), freq=freq)
        receiver.run(sampler, gain=1.0/amplitude, output=dst)
        return True
    except Exception:
        log.exception('Decoding failed')
        return False
    finally:
        dst.flush()
        receiver.report()
