from amodem import main
from amodem import common
from amodem import sampling
from amodem import config
import utils

import numpy as np
import os
from io import BytesIO

import pytest
import logging
logging.basicConfig(level=logging.DEBUG,  # useful for debugging
                    format='%(asctime)s %(levelname)-12s %(message)s')


def run(size, chan=None, df=0, success=True, cfg=None):
    if cfg is None:
        cfg = config.fastest()
    tx_data = os.urandom(size)
    tx_audio = BytesIO()
    main.send(config=cfg, src=BytesIO(tx_data), dst=tx_audio, gain=0.5)

    data = tx_audio.getvalue()
    data = common.loads(data)
    if chan is not None:
        data = chan(data)
    if df:
        sampler = sampling.Sampler(data, sampling.Interpolator())
        sampler.freq += df
        data = sampler.take(len(data))

    data = common.dumps(data)
    rx_audio = BytesIO(data)
    rx_data = BytesIO()
    dump = BytesIO()

    try:
        result = main.recv(config=cfg, src=rx_audio, dst=rx_data,
                           dump_audio=dump, pylab=None)
    finally:
        rx_audio.close()

    rx_data = rx_data.getvalue()
    assert data.startswith(dump.getvalue())

    assert result == success
    if success:
        assert rx_data == tx_data


@pytest.fixture(params=[0, 1, 3, 10, 16, 17, 42, 123])
def small_size(request):
    return request.param


@pytest.fixture(params=list(config.bitrates.values()))
def all_configs(request):
    return request.param


def test_small(small_size, all_configs):
    run(small_size, chan=lambda x: x, cfg=all_configs)


def test_flip():
    run(16, chan=lambda x: -x)


def test_large_drift():
    run(1, df=+0.01)
    run(1, df=-0.01)


def test_error():
    skip = 32000  # remove trailing silence
    run(1024, chan=lambda x: x[:-skip], success=False)


@pytest.fixture(params=[sign * mag for sign in (+1, -1)
                        for mag in (0.1, 1, 10, 100, 1e3, 10e3)])
def freq_err(request):
    return request.param * 1e-6


def test_timing(freq_err):
    run(8192, df=freq_err)


def test_lowpass():
    run(1024, chan=lambda x: utils.lfilter(b=[0.9], a=[1.0, -0.1], x=x))


def test_highpass():
    run(1024, chan=lambda x: utils.lfilter(b=[0.9], a=[1.0, 0.1], x=x))


def test_attenuation():
    run(5120, chan=lambda x: x * 0.1)


def test_low_noise():
    r = np.random.RandomState(seed=0)
    run(5120, chan=lambda x: x + r.normal(size=len(x), scale=0.0001))


def test_medium_noise():
    r = np.random.RandomState(seed=0)
    run(5120, chan=lambda x: x + r.normal(size=len(x), scale=0.001))


def test_large():
    run(54321, chan=lambda x: x)


@pytest.fixture(params=sorted(config.bitrates.keys()))
def rate(request):
    return request.param


def test_rate(rate):
    run(1, cfg=config.bitrates[rate])
