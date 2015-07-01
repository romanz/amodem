#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
from . import main, calib, audio, async
from .config import bitrates
from . import version

import os
import sys
import zlib
import logging
import argparse

# Python 3 has `buffer` attribute for byte-based I/O
_stdin = getattr(sys.stdin, 'buffer', sys.stdin)
_stdout = getattr(sys.stdout, 'buffer', sys.stdout)


try:
    import argcomplete
except ImportError:
    argcomplete = None

log = logging.getLogger('__name__')

bitrate = os.environ.get('BITRATE', 1)
config = bitrates.get(int(bitrate))


class Compressor(object):
    def __init__(self, stream):
        self.obj = zlib.compressobj()
        log.info('Using zlib compressor')
        self.stream = stream

    def read(self, size):
        while True:
            data = self.stream.read(size)
            if data:
                result = self.obj.compress(data)
                if not result:  # compression is too good :)
                    continue  # try again (since falsy data = EOF)
            elif self.obj:
                result = self.obj.flush()
                self.obj = None
            else:
                result = ''  # EOF marker
            return result


class Decompressor(object):
    def __init__(self, stream):
        self.obj = zlib.decompressobj()
        log.info('Using zlib decompressor')
        self.stream = stream

    def write(self, data):
        self.stream.write(self.obj.decompress(bytes(data)))

    def flush(self):
        self.stream.write(self.obj.flush())


def FileType(mode, interface_factory=None):
    def opener(fname):
        audio_interface = interface_factory() if interface_factory else None

        assert 'r' in mode or 'w' in mode
        if audio_interface is None and fname is None:
            fname = '-'

        if fname is None:
            assert audio_interface is not None
            if 'r' in mode:
                s = audio_interface.recorder()
                return async.AsyncReader(stream=s, bufsize=s.bufsize)
            if 'w' in mode:
                return audio_interface.player()

        if fname == '-':
            if 'r' in mode:
                return _stdin
            if 'w' in mode:
                return _stdout

        return open(fname, mode)

    return opener


def get_volume_cmd(args):
    volume_controllers = [
        dict(test='pactl --version',
             send='pactl set-sink-volume @DEFAULT_SINK@',
             recv='pactl set-source-volume @DEFAULT_SOURCE@')
    ]
    if args.calibrate == 'auto':
        for c in volume_controllers:
            if os.system(c['test']) == 0:
                return c[args.command]


def wrap(cls, stream, enable):
    return cls(stream) if enable else stream


def create_parser(description, interface_factory):
    p = argparse.ArgumentParser(description=description)
    subparsers = p.add_subparsers()

    # Modulator
    sender = subparsers.add_parser(
        'send', help='modulate binary data into audio signal.')
    sender.add_argument(
        '-i', '--input', help='input file (use "-" for stdin).')
    sender.add_argument(
        '-o', '--output', help='output file (use "-" for stdout).'
        ' if not specified, `aplay` tool will be used.')
    sender.add_argument(
        '-g', '--gain', type=float, default=1.0,
        help='Modulator gain (defaults to 1)')
    sender.set_defaults(
        main=lambda config, args: main.send(
            config, src=wrap(Compressor, args.src, args.zlib), dst=args.dst,
            gain=args.gain
        ),
        calib=lambda config, args: calib.send(
            config=config, dst=args.dst,
            volume_cmd=get_volume_cmd(args)
        ),
        input_type=FileType('rb'),
        output_type=FileType('wb', interface_factory),
        command='send'
    )

    # Demodulator
    receiver = subparsers.add_parser(
        'recv', help='demodulate audio signal into binary data.')
    receiver.add_argument(
        '-i', '--input', help='input file (use "-" for stdin).'
        ' if not specified, `arecord` tool will be used.')
    receiver.add_argument(
        '-o', '--output', help='output file (use "-" for stdout).')
    receiver.add_argument(
        '-d', '--dump', type=FileType('wb'),
        help='Filename to save recorded audio')
    receiver.add_argument(
        '--plot', action='store_true', default=False,
        help='plot results using pylab module')
    receiver.set_defaults(
        main=lambda config, args: main.recv(
            config, src=args.src, dst=wrap(Decompressor, args.dst, args.zlib),
            pylab=args.pylab, dump_audio=args.dump
        ),
        calib=lambda config, args: calib.recv(
            config=config, src=args.src, verbose=args.verbose,
            volume_cmd=get_volume_cmd(args)
        ),
        input_type=FileType('rb', interface_factory),
        output_type=FileType('wb'),
        command='recv'
    )

    calibration_help = ('Run calibration '
                        '(specify "auto" for automatic gain control)')

    for sub in subparsers.choices.values():
        sub.add_argument('-c', '--calibrate', nargs='?', default=False,
                         metavar='SYSTEM', help=calibration_help)
        sub.add_argument('-l', '--audio-library', default='libportaudio.so',
                         help='File name of PortAudio shared library.')
        sub.add_argument('-z', '--zlib', default=False, action='store_true',
                         help='Use zlib to compress/decompress data.')
        g = sub.add_mutually_exclusive_group()
        g.add_argument('-v', '--verbose', default=0, action='count')
        g.add_argument('-q', '--quiet', default=False, action='store_true')

    if argcomplete:
        argcomplete.autocomplete(p)

    return p


class _Dummy(object):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _main():
    fmt = ('Audio OFDM MODEM v{0:s}: '
           '{1:.1f} kb/s ({2:d}-QAM x {3:d} carriers) '
           'Fs={4:.1f} kHz')
    description = fmt.format(version.__doc__,
                             config.modem_bps / 1e3, len(config.symbols),
                             config.Nfreq, config.Fs / 1e3)
    interface = None

    def interface_factory():
        return interface

    p = create_parser(description, interface_factory)

    args = p.parse_args()
    if args.verbose == 0:
        level, fmt = 'INFO', '%(message)s'
    elif args.verbose == 1:
        level, fmt = 'DEBUG', '%(message)s'
    elif args.verbose >= 2:
        level, fmt = ('DEBUG', '%(asctime)s %(levelname)-10s '
                               '%(message)-100s '
                               '%(filename)s:%(lineno)d')
    if args.quiet:
        level, fmt = 'WARNING', '%(message)s'
    logging.basicConfig(level=level, format=fmt)

    # Parsing and execution
    log.debug(description)

    args.pylab = None
    if getattr(args, 'plot', False):
        import pylab  # pylint: disable=import-error
        args.pylab = pylab

    if args.audio_library == 'ALSA':
        from . import alsa
        interface = alsa.Interface(config)
    elif args.audio_library == '-':
        interface = _Dummy()
    else:
        interface = audio.Interface(config)
        interface.load(args.audio_library)

    with interface:
        args.src = args.input_type(args.input)
        args.dst = args.output_type(args.output)
        try:
            if args.calibrate is False:
                args.main(config=config, args=args)
            else:
                args.calib(config=config, args=args)
        finally:
            args.src.close()
            args.dst.close()
            log.debug('Finished I/O')


if __name__ == '__main__':
    _main()
