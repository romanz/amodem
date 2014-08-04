import os
from cStringIO import StringIO

import send
import recv
import common

class Args(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def run(chan, size):
    tx_data = os.urandom(size)
    tx_audio = StringIO()
    send.main(Args(silence_start=1, silence_stop=1, input=StringIO(tx_data), output=tx_audio))

    data = tx_audio.getvalue()
    data = common.loads(data)
    data = chan(data)
    data = common.dumps(data * 1j)
    rx_audio = StringIO(data)

    rx_data = StringIO()
    recv.main(Args(skip=100, input=rx_audio, output=rx_data))
    rx_data = rx_data.getvalue()

    assert rx_data == tx_data

def test_small():
    run(chan=lambda x: x, size=1024)

def test_large():
    run(chan=lambda x: x, size=64 << 10)
