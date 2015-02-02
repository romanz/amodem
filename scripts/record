#!/usr/bin/env python
import argparse
from amodem import audio
from amodem.config import Configuration


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-l', '--audio-library', default='libportaudio.so')
    p.add_argument('filename')
    args = p.parse_args()

    config = Configuration()
    with open(args.filename, 'wb') as dst:
        print dst
        interface = audio.Interface(config=config)
        with interface.load(args.audio_library):
            src = interface.recorder()
            size = int(config.sample_size * config.Fs)  # one second of audio
            while True:
                dst.write(src.read(size))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
