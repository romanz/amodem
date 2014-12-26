import subprocess as sp
import logging
import functools

log = logging.getLogger(__name__)

class ALSA(object):
    def __init__(self, tool, Fs):
        self.Fs = int(Fs)  # sampling rate
        self.bits_per_sample = 16
        self.bytes_per_sample = self.bits_per_sample / 8.0
        self.bytes_per_second = self.bytes_per_sample * self.Fs
        # PCM signed little endian
        self.audio_format = 'S{0}_LE'.format(self.bits_per_sample)
        self.audio_tool = tool

    def launch(self, fname=None, **kwargs):
        if fname is None:
            fname = '-'  # use stdin/stdout if filename not specified
        args = [self.audio_tool, fname, '-q',
                '-f', self.audio_format,
                '-c', '1',
                '-r', str(self.Fs)]
        log.debug('Running: %r', ' '.join(args))
        p = sp.Popen(args=args, **kwargs)
        return p

# Use ALSA tools for audio playing/recording
play = functools.partial(ALSA, tool='aplay')
record = functools.partial(ALSA, tool='arecord')
