"""Audio capabilities for amodem."""

import ctypes
import logging
import platform
import string
import time

log = logging.getLogger(__name__)

PLATFORM_IS_WIN = platform.system() == 'Windows'
WIN_ERR_CODES = ['pa.paNoError', 'pa.paNotInitialized', 'pa.paUnanticipatedHostError', 'pa.paInvalidChannelCount',
                 'pa.paInvalidSampleRate', 'pa.paInvalidDevice', 'pa.paInvalidFlag', 'pa.paSampleFormatNotSupported',
                 'pa.paBadIODeviceCombination', 'pa.paInsufficientMemory', 'pa.paBufferTooBig', 'pa.paBufferTooSmall',
                 'pa.paNullCallback', 'pa.paBadStreamPtr', 'pa.paTimedOut', 'pa.paInternalError',
                 'pa.paDeviceUnavailable', 'pa.paIncompatibleHostApiSpecificStreamInfo', 'pa.paStreamIsStopped',
                 'pa.paStreamIsNotStopped', 'pa.paInputOverflowed', 'pa.paOutputUnderflowed', 'pa.paHostApiNotFound',
                 'pa.paInvalidHostApi', 'pa.paCanNotReadFromACallbackStream', 'pa.paCanNotWriteToACallbackStream',
                 'pa.paCanNotReadFromAnOutputOnlyStream', 'pa.paCanNotWriteToAnInputOnlyStream',
                 'pa.paIncompatibleStreamHostApi']
WIN_ERR_CODE_MAP = {}


class Interface:
    def __init__(self, config, debug=False):
        self.debug = bool(debug)
        self.config = config
        self.streams = []
        self.lib = None

        self.win_pyaudio = None
        self.win_err_code_map = {}
        self.win_func_names = []
        self.win_mapped_func = {}

    def load(self, name):
        if PLATFORM_IS_WIN:
            import pyaudio as pa
            self.lib = pa._portaudio
            self.win_pyaudio = pa.PyAudio()
            self.win_func_names = dir(self.lib)
            for code_str in WIN_ERR_CODES:
                WIN_ERR_CODE_MAP[eval(code_str)] = code_str[3:]
            WIN_ERR_CODE_MAP[0] = b'Success'
        else:
            self.lib = ctypes.CDLL(name)
        assert self._error_string(0) == b'Success'
        version = self.call('GetVersionText', restype=ctypes.c_char_p)
        log.info('%s loaded', version)
        return self

    def _error_string(self, code):
        if PLATFORM_IS_WIN:
            return WIN_ERR_CODE_MAP.get(code, "Unknown Error")
        else:
            return self.call('GetErrorText', code, restype=ctypes.c_char_p)

    def call(self, name, *args, **kwargs):
        assert self.lib is not None
        if PLATFORM_IS_WIN:
            if name in self.win_mapped_func:
                func_name = self.win_mapped_func[name]
            else:
                func_name = ""
                for c, ch in enumerate(name):
                    if c > 0 and ch in string.ascii_uppercase:
                        func_name += f"_{ch.lower()}"
                    else:
                        func_name += ch.lower()
            if self.debug:
                log.debug('API: %s%s', name, args)
            if func_name in self.win_func_names:
                func = getattr(self.lib, func_name)
                if hasattr(func, "restype"):
                    func.restype = kwargs.get('restype', self._error_check)
                try:
                    return func(*args)
                except Exception as e:
                    log.error(f"call [{name}], args [{args}], kwargs [{kwargs}]")
                    raise e
            else:
                raise Exception("No such method", func_name)
        else:
            func_name = f'Pa_{name}'
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
        self.bufsize = int(2 * self.latency * config.Fs * self.bytes_per_sample)
        assert config.bits_per_sample == 16  # just to make sure :)

        read = bool(read)
        write = bool(write)
        assert read != write  # don't support full duplex

        if PLATFORM_IS_WIN:
            import pyaudio as pa
            arguments = {
                'rate': int(config.Fs),
                'channels': 1,
                'format': pa.paInt16,
                'input': read,
                'output': write,
                'frames_per_buffer': pa.paFramesPerBufferUnspecified,
            }
            self.stream = self.interface.win_pyaudio.open(**arguments)
            self.interface.streams.append(self)
            self.stream.start_stream()
        else:
            direction = 'Input' if read else 'Output'
            api_name = f'GetDefault{direction}Device'
            index = interface.call(api_name, restype=ctypes.c_int)
            self.params = Stream.Parameters(
                device=index,  # choose default device
                channelCount=1,  # mono audio
                sampleFormat=0x00000008,  # 16-bit samples (paInt16)
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
            if PLATFORM_IS_WIN:
                self.stream.stop_stream()
                self.stream.close()
            else:
                self.interface.call('StopStream', self.stream)
                self.interface.call('CloseStream', self.stream)
            self.stream = None

    def read(self, size):
        assert size % self.bytes_per_sample == 0
        if PLATFORM_IS_WIN:
            class _tmp:
                def __init__(self):
                    self.raw = None

            t0 = self.timer()
            buf = _tmp()
            buf.raw = self.stream.read((size // self.bytes_per_sample))
        else:
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
        if PLATFORM_IS_WIN:
            self.stream.write(data, num_frames=(len(data) // self.bytes_per_sample))
        else:
            buf = ctypes.c_char_p(data)
            frames = ctypes.c_ulong(len(data) // self.bytes_per_sample)
            self.interface.call('WriteStream', self.stream, buf, frames)
