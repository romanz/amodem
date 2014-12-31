import pyaudio
import logging

log = logging.getLogger(__name__)


class Interface(object):
    def __init__(self, config, library=pyaudio):
        self.p = library.PyAudio()
        fmt = getattr(library, 'paInt{0}'.format(config.bits_per_sample))
        self.sample_size = config.sample_size
        self.kwargs = dict(
            channels=1, rate=int(config.Fs), format=fmt,
            frames_per_buffer=config.samples_per_buffer
        )

    def __del__(self):
        self.p.terminate()

    def player(self):
        return self.p.open(output=True, **self.kwargs)

    def recorder(self):
        stream = self.p.open(input=True, **self.kwargs)
        return _Recorder(stream, sample_size=self.sample_size)


class _Recorder(object):
    def __init__(self, stream, sample_size):
        self.stream = stream
        self.sample_size = sample_size

    def read(self, size):
        assert size % self.sample_size == 0
        return self.stream.read(size // self.sample_size)
