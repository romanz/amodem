#!/usr/bin/env python
import bitarray
import sys

tx_fname, rx_fname = sys.argv[1:]
tx = bitarray.bitarray()
tx.fromfile(open(tx_fname))

rx = bitarray.bitarray()
rx.fromfile(open(rx_fname))

L = min(len(tx), len(rx))
if L == 0:
    sys.exit(1)

rx = rx[:L]
tx = tx[:L]
errors = (rx ^ tx).count(1)
total = L
ber = float(errors) / total  # bit error rate
print('BER: {:.3f}% ({}/{})'.format(100 * ber, errors, total))
sys.exit(int(errors > 0))
