import functools
import itertools
import logging
import time

import numpy as np

from . import dsp
from . import common
from . import framing
from . import equalizer

log = logging.getLogger(__name__)


class Receiver:

    def __init__(self, config, pylab=None):
        self.stats = {}
        self.plt = pylab
        self.modem = dsp.MODEM(config.symbols)
        self.frequencies = np.array(config.frequencies)
        self.omegas = 2 * np.pi * self.frequencies / config.Fs
        self.Nsym = config.Nsym
        self.Tsym = config.Tsym
        self.iters_per_update = 100  # [ms]
        self.iters_per_report = 1000  # [ms]
        self.modem_bitrate = config.modem_bps
        self.equalizer = equalizer.Equalizer(config)
        self.carrier_index = config.carrier_index
        self.output_size = 0  # number of bytes written to output stream
        self.freq_err_gain = 0.01 * self.Tsym  # integration feedback gain

    def _prefix(self, symbols, gain=1.0):
        S = common.take(symbols, len(equalizer.prefix))
        S = S[:, self.carrier_index] * gain
        sliced = np.round(np.abs(S))
        self.plt.figure()
        self.plt.subplot(1, 2, 1)
        self._constellation(S, sliced, 'Prefix')

        bits = np.array(sliced, dtype=int)
        self.plt.subplot(1, 2, 2)
        self.plt.plot(np.abs(S))
        self.plt.plot(equalizer.prefix)
        errors = (bits != equalizer.prefix)
        if any(errors):
            msg = f'Incorrect prefix: {sum(errors)} errors'
            raise ValueError(msg)
        log.debug('Prefix OK')

    def _train(self, sampler, order, lookahead):
        equalizer_length = equalizer.equalizer_length
        train_symbols = self.equalizer.train_symbols(equalizer_length)
        train_signal = (self.equalizer.modulator(train_symbols) *
                        len(self.frequencies))

        prefix = postfix = equalizer.silence_length * self.Nsym
        signal_length = equalizer_length * self.Nsym + prefix + postfix

        signal = sampler.take(signal_length + lookahead)

        coeffs = equalizer.train(
            signal=signal[prefix:-postfix],
            expected=np.concatenate([train_signal, np.zeros(lookahead)]),
            order=order, lookahead=lookahead
        )

        self.plt.figure()
        self.plt.plot(np.arange(order+lookahead), coeffs)

        equalization_filter = dsp.FIR(h=coeffs)
        log.debug('Training completed')
        # Pre-load equalization filter with the signal (+lookahead)
        equalized = list(equalization_filter(signal))
        equalized = equalized[prefix+lookahead:-postfix+lookahead]
        self._verify_training(equalized, train_symbols)
        return equalization_filter

    def _verify_training(self, equalized, train_symbols):
        equalizer_length = equalizer.equalizer_length
        symbols = self.equalizer.demodulator(equalized, equalizer_length)
        sliced = np.array(symbols).round()
        errors = np.array(sliced - train_symbols, dtype=bool)
        error_rate = errors.sum() / errors.size

        errors = np.array(symbols - train_symbols)

        noise_rms = dsp.rms(errors)
        signal_rms = dsp.rms(train_symbols)
        SNRs = 20.0 * np.log10(signal_rms / noise_rms)

        self.plt.figure()
        for (i, freq), snr in zip(enumerate(self.frequencies), SNRs):
            log.debug('%5.1f kHz: SNR = %5.2f dB', freq / 1e3, snr)
            self._constellation(symbols[:, i], train_symbols[:, i],
                                f'$F_c = {freq} Hz$', index=i)
        assert error_rate == 0, error_rate
        log.debug('Training verified')

    def _bitstream(self, symbols, error_handler):
        streams = []
        symbol_list = []
        generators = common.split(symbols, n=len(self.omegas))
        for freq, S in zip(self.frequencies, generators):
            equalized = []
            S = common.icapture(S, result=equalized)
            symbol_list.append(equalized)

            freq_handler = functools.partial(error_handler, freq=freq)
            bits = self.modem.decode(S, freq_handler)  # list of bit tuples
            streams.append(bits)  # bit stream per frequency

        return zip(*streams), symbol_list

    def _demodulate(self, sampler, symbols):
        symbol_list = []
        errors = {}
        noise = {}

        def _handler(received, decoded, freq):
            errors.setdefault(freq, []).append(received / decoded)
            noise.setdefault(freq, []).append(received - decoded)

        stream, symbol_list = self._bitstream(symbols, _handler)
        self.stats['symbol_list'] = symbol_list
        self.stats['rx_bits'] = 0
        self.stats['rx_start'] = time.time()

        log.info('Starting demodulation')
        for i, block_of_bits in enumerate(stream, 1):
            for bits in block_of_bits:
                self.stats['rx_bits'] = self.stats['rx_bits'] + len(bits)
                yield bits

            if i % self.iters_per_update == 0:
                self._update_sampler(errors, sampler)

            if i % self.iters_per_report == 0:
                self._report_progress(noise, sampler)

    def _update_sampler(self, errors, sampler):
        err = np.array([e for v in errors.values() for e in v])
        err = np.mean(np.angle(err))/(2*np.pi) if err.size else 0
        errors.clear()

        sampler.freq -= self.freq_err_gain * err
        sampler.offset -= err

    def _report_progress(self, noise, sampler):
        e = np.array([e for v in noise.values() for e in v])
        noise.clear()
        log.debug(
            'Got  %10.3f kB, SNR: %5.2f dB, drift: %+5.2f ppm',
            self.stats['rx_bits'] / 8e3,
            -10 * np.log10(np.mean(np.abs(e) ** 2)),
            (1.0 - sampler.freq) * 1e6
        )

    def run(self, sampler, gain, output):
        log.debug('Receiving')
        symbols = dsp.Demux(sampler, omegas=self.omegas, Nsym=self.Nsym)
        self._prefix(symbols, gain=gain)

        filt = self._train(sampler, order=10, lookahead=10)
        sampler.equalizer = lambda x: list(filt(x))

        bitstream = self._demodulate(sampler, symbols)
        bitstream = itertools.chain.from_iterable(bitstream)

        for frame in framing.decode_frames(bitstream):
            output.write(frame)
            self.output_size += len(frame)

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
                                    f'$F_c = {freq} Hz$', index=i)
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
