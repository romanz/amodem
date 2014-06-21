import common
import sys

tx, rx = sys.argv[1:]
tx = open(tx).read()
rx = open(rx).read()

L = min(len(tx), len(rx))
rx = list(common.to_bits(rx[:L]))
tx = list(common.to_bits(tx[:L]))
indices = [index for index, (r, t) in enumerate(zip(rx, tx)) if r != t]

if indices:
    total = L*8
    errors = len(indices)
    print('{}/{} bit error rate: {:.3f}%'.format(errors, total, (100.0 * errors) / total))
    sys.exit(1)
