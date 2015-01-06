import ctypes
import logging

log = logging.getLogger(__name__)


class Library(object):
    def __init__(self, name):
        self.lib = ctypes.CDLL(name)
        self.streams = []
        assert self._error_string(0) == 'Success'

    def _error_string(self, code):
        return self.call('GetErrorText', code, restype=ctypes.c_char_p)

    def call(self, name, *args, **kwargs):
        func = getattr(self.lib, 'Pa_{0}'.format(name))
        func.restype = kwargs.get('restype', self._error_check)
        return func(*args)

    def _error_check(self, res):
        if res != 0:
            raise Exception(res, self._error_string(res))

    def __enter__(self):
        self.call('Initialize')
        return self

    def __exit__(self, *args):
        for s in self.streams:
            s.close()
        self.call('Terminate')

    def recorder(self):
        return Stream(self, read=True)

    def player(self):
        return Stream(self, write=True)


class Stream(object):

    class Parameters(ctypes.Structure):
        _fields_ = [
            ('device', ctypes.c_int),
            ('channelCount', ctypes.c_int),
            ('sampleFormat', ctypes.c_ulong),
            ('suggestedLatency', ctypes.c_double),
            ('hostApiSpecificStreamInfo', ctypes.POINTER(None)),
        ]

    sample_rate = 32000.0
    frames_per_buffer = 4096
    suggested_latency = 0.1
    channel_count = 1
    sample_format = 0x00000008  # 16-bit samples (paInt16)
    bytes_per_sample = 2
    flags = 0  # no flags (paNoFlag)

    def __init__(self, lib, read=False, write=False):
        self.lib = lib
        self.stream = ctypes.POINTER(ctypes.c_void_p)()
        self.user_data = ctypes.c_void_p(None)
        self.stream_callback = ctypes.c_void_p(None)

        index = lib.call('GetDefaultInputDevice', restype=ctypes.c_int)
        self.params = Stream.Parameters(
            device=index,
            channelCount=self.channel_count,
            sampleFormat=self.sample_format,
            suggestedLatency=self.suggested_latency,
            hostApiSpecificStreamInfo=None)

        self.lib.call(
            'OpenStream',
            ctypes.byref(self.stream),
            ctypes.byref(self.params) if read else None,
            ctypes.byref(self.params) if write else None,
            ctypes.c_double(self.sample_rate),
            ctypes.c_ulong(self.frames_per_buffer),
            ctypes.c_ulong(self.flags),
            self.stream_callback,
            self.user_data)

        self.lib.streams.append(self)
        self.lib.call('StartStream', self.stream)

    def close(self):
        if self.stream:
            self.lib.call('StopStream', self.stream)
            self.lib.call('CloseStream', self.stream)
            self.stream = None

    def read(self, size):
        assert size % self.bytes_per_sample == 0
        buf = ctypes.create_string_buffer(size)
        frames = ctypes.c_ulong(size // self.bytes_per_sample)
        self.lib.call('ReadStream', self.stream, buf, frames)
        return buf.raw

    def write(self, data):
        data = bytes(data)
        assert len(data) % self.bytes_per_sample == 0
        buf = ctypes.c_char_p(data)
        frames = ctypes.c_ulong(len(data) // self.bytes_per_sample)
        self.lib.call('WriteStream', self.stream, buf, frames)
