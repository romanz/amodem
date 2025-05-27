"""
Code which adds sounddevice lib support for interfaces, recording and playing.
"""

import logging
import sounddevice as sd

log = logging.getLogger(__name__)


class Interface:

    def __init__(self, config):
        self.config = config
        bits_per_sample = config.bits_per_sample
        assert bits_per_sample == 16

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def recorder(self):
        return Recorder(self)

    def player(self):
        return Player(self)


class Recorder:
    def __init__(self, lib):
        self.bufsize = 4096

        self.audio_stream = sd.RawInputStream(
            samplerate=lib.config.Fs,
            device=lib.config.input_device_index,
            blocksize=self.bufsize,
            channels=1, dtype='int16')
        self.audio_stream.start()

    def read(self, size):
        data, overflowed = self.audio_stream.read(size)
        if overflowed:
            raise OverflowError("Overflow reading from audio device")
        return data

    def close(self):
        self.audio_stream.stop()
        self.audio_stream.close()


class Player:
    def __init__(self, lib):
        self.buffer_length_ms = 10
        self.buffer_size = int(lib.config.Fs * (self.buffer_length_ms / 1000))

        self.audio_stream = sd.RawOutputStream(
            samplerate=lib.config.Fs,
            device=lib.config.output_device_index,
            blocksize=self.buffer_size,
            channels=1, dtype='int16')

        self.audio_stream.start()

    def write(self, data):
        self.audio_stream.write(data)

    def close(self):
        self.audio_stream.stop()
        self.audio_stream.close()
