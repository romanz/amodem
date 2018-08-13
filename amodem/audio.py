"""Audio capabilities for amodem."""

import ctypes
import logging
import time

log = logging.getLogger(__name__)


class Interface:
    def __init__(self, config, debug=False):
        self.debug = bool(debug)
        self.config = config
        self.streams = []
        self.lib = None

    def load(self, name):
        self.lib = ctypes.CDLL(name)
        assert self._error_string(0) == b'Success'
        version = self.call('GetVersionText', restype=ctypes.c_char_p)
        log.info('%s loaded', version)
        return self

    def _error_string(self, code):
        return self.call('GetErrorText', code, restype=ctypes.c_char_p)

    def call(self, name, *args, **kwargs):
        assert self.lib is not None
        func_name = 'Pa_{0}'.format(name)
        if self.debug:
            log.debug('API: %s%s', name, args)
        func = getattr(self.lib, func_name)
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
        return Stream(self, config=self.config, read=True)

    def player(self):
        return Stream(self, config=self.config, write=True)


class Stream:

    timer = time.time

    class Parameters(ctypes.Structure):
        _fields_ = [
            ('device', ctypes.c_int),
            ('channelCount', ctypes.c_int),
            ('sampleFormat', ctypes.c_ulong),
            ('suggestedLatency', ctypes.c_double),
            ('hostApiSpecificStreamInfo', ctypes.POINTER(None))
        ]

    def __init__(self, interface, config, read=False, write=False):
        self.interface = interface
        self.stream = ctypes.POINTER(ctypes.c_void_p)()
        self.user_data = ctypes.c_void_p(None)
        self.stream_callback = ctypes.c_void_p(None)
        self.bytes_per_sample = config.sample_size
        self.latency = float(config.latency)  # in seconds
        self.bufsize = int(self.latency * config.Fs * self.bytes_per_sample)
        assert config.bits_per_sample == 16  # just to make sure :)

        read = bool(read)
        write = bool(write)
        assert read != write  # don't support full duplex

        direction = 'Input' if read else 'Output'
        api_name = 'GetDefault{0}Device'.format(direction)
        index = interface.call(api_name, restype=ctypes.c_int)
        self.params = Stream.Parameters(
            device=index,               # choose default device
            channelCount=1,             # mono audio
            sampleFormat=0x00000008,    # 16-bit samples (paInt16)
            suggestedLatency=self.latency,
            hostApiSpecificStreamInfo=None)

        self.interface.call(
            'OpenStream',
            ctypes.byref(self.stream),
            ctypes.byref(self.params) if read else None,
            ctypes.byref(self.params) if write else None,
            ctypes.c_double(config.Fs),
            ctypes.c_ulong(0),  # (paFramesPerBufferUnspecified)
            ctypes.c_ulong(0),  # no flags (paNoFlag)
            self.stream_callback,
            self.user_data)

        self.interface.streams.append(self)
        self.interface.call('StartStream', self.stream)
        self.start_time = self.timer()
        self.io_time = 0

    def close(self):
        if self.stream:
            self.interface.call('StopStream', self.stream)
            self.interface.call('CloseStream', self.stream)
            self.stream = None

    def read(self, size):
        assert size % self.bytes_per_sample == 0
        buf = ctypes.create_string_buffer(size)
        frames = ctypes.c_ulong(size // self.bytes_per_sample)
        t0 = self.timer()
        self.interface.call('ReadStream', self.stream, buf, frames)
        t1 = self.timer()
        self.io_time += (t1 - t0)
        if self.interface.debug:
            io_wait = self.io_time / (t1 - self.start_time)
            log.debug('I/O wait: %.1f%%', io_wait * 100)
        return buf.raw

    def write(self, data):
        data = bytes(data)
        assert len(data) % self.bytes_per_sample == 0
        buf = ctypes.c_char_p(data)
        frames = ctypes.c_ulong(len(data) // self.bytes_per_sample)
        self.interface.call('WriteStream', self.stream, buf, frames)
