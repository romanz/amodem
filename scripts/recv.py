import sys
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-12s %(message)s')

import argparse
p = argparse.ArgumentParser()
p.add_argument('--skip', type=int, default=100,
               help='skip initial N samples, due to spurious spikes')
p.add_argument('-i', '--input', type=argparse.FileType('rb'),
               default=sys.stdin)
p.add_argument('-o', '--output', type=argparse.FileType('wb'),
               default=sys.stdout)
args = p.parse_args()

from amodem.recv import main
main(args)
