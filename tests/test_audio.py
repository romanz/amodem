from amodem import audio

import mock
import pytest


def test():
    length = 1024
    data = b'\x12\x34' * length
    with mock.patch('ctypes.CDLL') as cdll:
        lib = mock.Mock()
        lib.Pa_GetErrorText = lambda code: 'Error' if code else 'Success'
        lib.Pa_GetDefaultInputDevice.return_value = 1
        lib.Pa_OpenStream.return_value = 0
        cdll.return_value = lib
        interface = audio.Library('portaudio')
        with interface:
            s = interface.player()
            s.stream = 1  # simulate non-zero output stream handle
            s.write(data=data)
            s.close()

        with interface:
            s = interface.recorder()
            s.stream = 2  # simulate non-zero input stream handle
            s.read(len(data))
            s.close()

        with pytest.raises(Exception):
            interface._error_check(1)
