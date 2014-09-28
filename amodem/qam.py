import numpy as np
from . import common


class QAM(object):

    buf_size = 16

    def __init__(self, symbols):
        self.encode_map = {}
        symbols = np.array(list(symbols))
        bits_per_symbol = np.log2(len(symbols))
        bits_per_symbol = np.round(bits_per_symbol)
        N = (2 ** bits_per_symbol)
        assert N == len(symbols)
        bits_per_symbol = int(bits_per_symbol)

        for i, v in enumerate(symbols):
            bits = [int(i & (1 << j) != 0) for j in range(bits_per_symbol)]
            self.encode_map[tuple(bits)] = v

        self.symbols = symbols
        self.bits_per_symbol = bits_per_symbol

        bits_map = {symbol: bits for bits, symbol in self.encode_map.items()}
        self.decode_list = [(s, bits_map[s]) for s in self.symbols]

    def encode(self, bits):
        for bits_tuple in common.iterate(bits, self.bits_per_symbol, tuple):
            yield self.encode_map[bits_tuple]

    def decode(self, symbols, error_handler=None):
        symbols_vec = self.symbols
        _dec = self.decode_list
        for syms in common.iterate(symbols, self.buf_size, truncate=False):
            for received in syms:
                error = np.abs(symbols_vec - received)
                index = np.argmin(error)
                decoded, bits = _dec[index]
                if error_handler:
                    error_handler(received=received, decoded=decoded)
                yield bits
