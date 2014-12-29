from amodem import audio
from amodem import config

import mock


def test_pyaudio_mock():
    m = mock.Mock()
    m.paInt16 = 8
    m.PyAudio.return_value = m
    m.open.return_value = m

    cfg = config.fastest()
    interface = audio.Interface(config=cfg, library=m)
    recorder = interface.recorder()
    n = 1024
    data = recorder.read(n)

    data = '\x00' * n
    player = interface.player()
    player.write(data)

    kwargs = dict(
        channels=1, frames_per_buffer=cfg.samples_per_buffer,
        rate=cfg.Fs, format=m.paInt16
    )
    assert m.mock_calls == [
        mock.call.PyAudio(),
        mock.call.open(input=True, **kwargs),
        mock.call.read(n // cfg.sample_size),
        mock.call.open(output=True, **kwargs),
        mock.call.write(data)
    ]
