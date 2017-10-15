#!/usr/bin/env python

"""Script that records audio through an interface
and stores it into an amodem.config Configuration.

"""
import argparse
from amodem import audio
from amodem.config import Configuration


def run(args):
    config = Configuration()
    with open(args.filename, 'wb') as dst:
        interface = audio.Interface(config=config)
        with interface.load(args.audio_library):
            src = interface.recorder()
            size = int(config.sample_size * config.Fs)  # one second of audio
            while True:
                dst.write(src.read(size))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-l', '--audio-library', default='libportaudio.so')
    p.add_argument('filename')

    try:
        run(args=p.parse_args())
    except KeyboardInterrupt:
        return


if __name__ == '__main__':
    main()
