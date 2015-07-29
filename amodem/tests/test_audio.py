from amodem import audio, config

import mock
import pytest


def test():
    length = 1024
    data = b'\x12\x34' * length
    with mock.patch('ctypes.CDLL') as cdll:
        lib = mock.Mock()
        lib.Pa_GetErrorText = lambda code: b'Error' if code else b'Success'
        lib.Pa_GetDefaultOutputDevice.return_value = 1
        lib.Pa_GetDefaultInputDevice.return_value = 2
        lib.Pa_OpenStream.return_value = 0
        cdll.return_value = lib
        interface = audio.Interface(config=config.fastest(), debug=True)
        assert interface.load(name='portaudio') is interface
        with interface:
            s = interface.player()
            assert s.params.device == 1
            s.stream = 1  # simulate non-zero output stream handle
            s.write(data=data)
            s.close()

        with interface:
            s = interface.recorder()
            assert s.params.device == 2
            s.stream = 2  # simulate non-zero input stream handle
            s.read(len(data))
            s.close()

        with pytest.raises(Exception):
            interface._error_check(1)
