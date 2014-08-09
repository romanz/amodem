import sys
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-12s %(message)s')

import argparse
p = argparse.ArgumentParser()
p.add_argument('--silence-start', type=float, default=1.0)
p.add_argument('--silence-stop', type=float, default=1.0)
p.add_argument('-i', '--input', type=argparse.FileType('rb'),
               default=sys.stdin)
p.add_argument('-o', '--output', type=argparse.FileType('wb'),
               default=sys.stdout)
args = p.parse_args()

from amodem.send import main
main(args)
