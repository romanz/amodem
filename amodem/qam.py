import numpy as np
from . import common


class QAM(object):

    buf_size = 16

    def __init__(self, symbols):
        self._enc = {}
        symbols = np.array(list(symbols))
        bits_per_symbol = np.log2(len(symbols))
        bits_per_symbol = np.round(bits_per_symbol)
        N = (2 ** bits_per_symbol)
        assert N == len(symbols)
        bits_per_symbol = int(bits_per_symbol)

        for i, v in enumerate(symbols):
            bits = [int(i & (1 << j) != 0) for j in range(bits_per_symbol)]
            self._enc[tuple(bits)] = v

        self._dec = {v: k for k, v in self._enc.items()}
        self.symbols = symbols
        self.bits_per_symbol = bits_per_symbol

        reals = np.array(list(sorted(set(symbols.real))))
        imags = np.array(list(sorted(set(symbols.imag))))

        _mean = lambda u: float(sum(u))/len(u) if len(u) else 1.0
        self.real_factor = 1.0 / _mean(np.diff(reals))
        self.imag_factor = 1.0 / _mean(np.diff(imags))
        self.bias = reals[0] + 1j * imags[0]

        self.symbols_map = {}
        for S in symbols:
            s = S - self.bias
            real_index = round(s.real * self.real_factor)
            imag_index = round(s.imag * self.imag_factor)
            self.symbols_map[real_index + 1j * imag_index] = (S, self._dec[S])
        self.real_max = max(k.real for k in self.symbols_map)
        self.imag_max = max(k.imag for k in self.symbols_map)

    def encode(self, bits):
        for bits_tuple in common.iterate(bits, self.bits_per_symbol, tuple):
            yield self._enc[bits_tuple]

    def decode(self, symbols, error_handler=None):
        symbols_map = self.symbols_map
        for syms in common.iterate(symbols, self.buf_size, truncate=False):
            s = syms - self.bias
            real_index = np.clip(s.real * self.real_factor, 0, self.real_max)
            imag_index = np.clip(s.imag * self.imag_factor, 0, self.imag_max)

            keys = np.round(real_index + 1j * imag_index)
            for key, received in zip(keys, syms):
                decoded_symbol, bits = symbols_map[key]
                if error_handler:
                    error_handler(received=received, decoded=decoded_symbol)
                yield bits
