import sys
import argparse
import logging
log = logging.getLogger(__name__)

import trezor
import server

def main():
    fmt = '%(asctime)s %(levelname)-12s %(message)-100s [%(filename)s]'
    p = argparse.ArgumentParser()
    p.add_argument('-k', '--key-label',
                   metavar='LABEL', dest='labels', action='append', default=[])
    p.add_argument('-v', '--verbose', action='count', default=0)
    p.add_argument('command', type=str, nargs='*')
    args = p.parse_args()

    verbosity = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = verbosity[min(args.verbose, len(verbosity) - 1)]
    logging.basicConfig(level=level, format=fmt)

    client = trezor.Client()

    key_files = []
    for label in args.labels:
        pubkey = client.get_public_key(label=label)
        key_files.append(trezor.export_public_key(pubkey=pubkey, label=label))

    if not args.command:
        sys.stdout.write(''.join(key_files))
        return

    signer = client.sign_ssh_challenge

    try:
        server.serve(key_files=key_files, command=args.command, signer=signer)
    except KeyboardInterrupt:
        log.info('server stopped')
    except Exception as e:
        log.warning(e, exc_info=True)

if __name__ == '__main__':
    main()
