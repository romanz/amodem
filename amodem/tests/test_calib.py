from amodem import calib
from amodem import common
from amodem import config

from io import BytesIO

import numpy as np
import random
import pytest
import mock

config = config.fastest()


class ProcessMock:
    def __init__(self):
        self.buf = BytesIO()
        self.stdin = self
        self.stdout = self
        self.bytes_per_sample = 2

    def write(self, data):
        assert self.buf.tell() < 10e6
        self.buf.write(data)

    def read(self, n):
        return self.buf.read(n)


def test_success():
    p = ProcessMock()
    calib.send(config, p, gain=0.5, limit=32)
    p.buf.seek(0)
    calib.recv(config, p)


def test_too_strong():
    p = ProcessMock()
    calib.send(config, p, gain=1.001, limit=32)
    p.buf.seek(0)
    for r in calib.detector(config, src=p):
        assert not r['success']
        assert r['msg'] == 'too strong signal'


def test_too_weak():
    p = ProcessMock()
    calib.send(config, p, gain=0.01, limit=32)
    p.buf.seek(0)
    for r in calib.detector(config, src=p):
        assert not r['success']
        assert r['msg'] == 'too weak signal'


def test_too_noisy():
    r = random.Random(0)  # generate random binary signal
    signal = np.array([r.choice([-1, 1]) for i in range(int(config.Fs))])
    src = BytesIO(common.dumps(signal * 0.5))
    for r in calib.detector(config, src=src):
        assert not r['success']
        assert r['msg'] == 'too noisy signal'


def test_errors():
    class WriteError(ProcessMock):
        def write(self, data):
            raise KeyboardInterrupt()
    p = WriteError()
    with pytest.raises(KeyboardInterrupt):
        calib.send(config, p, limit=32)
    assert p.buf.tell() == 0

    class ReadError(ProcessMock):
        def read(self, n):
            raise KeyboardInterrupt()
    p = ReadError()
    with pytest.raises(KeyboardInterrupt):
        calib.recv(config, p, verbose=True)
    assert p.buf.tell() == 0


@pytest.fixture(params=[0] + [sign * mag for sign in (+1, -1)
                              for mag in (0.1, 1, 10, 100, 1e3, 2e3)])
def freq_err(request):
    return request.param * 1e-6


def test_drift(freq_err):
    freq = config.Fc * (1 + freq_err / 1e6)
    t = np.arange(int(1.0 * config.Fs)) * config.Ts
    frame_length = 100
    rms = 0.5
    signal = rms * np.cos(2 * np.pi * freq * t)
    src = BytesIO(common.dumps(signal))
    iters = 0
    for r in calib.detector(config, src, frame_length=frame_length):
        assert r['success'] is True
        assert abs(r['rms'] - rms) < 1e-3
        assert abs(r['total'] - rms) < 1e-3
        iters += 1

    assert iters > 0
    assert iters == config.baud / frame_length


def test_volume():
    with mock.patch('subprocess.check_call') as check_call:
        ctl = calib.volume_controller('volume-control')
        ctl(0.01)
        ctl(0.421)
        ctl(0.369)
        ctl(1)
        assert check_call.mock_calls == [
            mock.call(shell=True, args='volume-control 1%'),
            mock.call(shell=True, args='volume-control 42%'),
            mock.call(shell=True, args='volume-control 37%'),
            mock.call(shell=True, args='volume-control 100%')
        ]
        with pytest.raises(AssertionError):
            ctl(0)
        with pytest.raises(AssertionError):
            ctl(-0.5)
        with pytest.raises(AssertionError):
            ctl(12.3)


def test_send_max_volume():
    with mock.patch('subprocess.check_call') as check_call:
        calib.send(config, dst=BytesIO(), volume_cmd='ctl', limit=1)
    assert check_call.mock_calls == [mock.call(shell=True, args='ctl 100%')]


def test_recv_binary_search():
    buf = BytesIO()
    gains = [0.5, 0.25, 0.38, 0.44, 0.41, 0.39, 0.40, 0.40]
    for gain in gains:
        calib.send(config, buf, gain=gain, limit=2)
    buf.seek(0)

    dump = BytesIO()
    with mock.patch('subprocess.check_call') as check_call:
        calib.recv(config, src=buf, volume_cmd='ctl', dump_audio=dump)
    assert dump.getvalue() == buf.getvalue()

    gains.append(gains[-1])
    fmt = 'ctl {0:.0f}%'
    expected = [mock.call(shell=True, args=fmt.format(100 * g)) for g in gains]
    assert check_call.mock_calls == expected


def test_recv_freq_change():
    p = ProcessMock()
    calib.send(config, p, gain=0.5, limit=2)
    offset = p.buf.tell() // 16
    p.buf.seek(offset)
    messages = [state['msg'] for state in calib.recv_iter(config, p)]
    assert messages == [
        'good signal', 'good signal', 'good signal',
        'frequency change',
        'good signal', 'good signal', 'good signal']
