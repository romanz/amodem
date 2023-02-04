import io
import os
import socket
import tempfile
import threading

import mock
import pytest

from .. import server, util
from ..ssh import protocol


def test_socket():
    path = tempfile.mktemp()
    with server.unix_domain_socket_server(path):
        pass
    assert not os.path.isfile(path)


class FakeSocket:

    def __init__(self, data=b''):
        self.rx = io.BytesIO(data)
        self.tx = io.BytesIO()

    def sendall(self, data):
        self.tx.write(data)

    def recv(self, size):
        return self.rx.read(size)

    def close(self):
        pass

    def settimeout(self, value):
        pass


def empty_device():
    c = mock.Mock(spec=['parse_public_keys'])
    c.parse_public_keys.return_value = []
    return c


def test_handle():
    mutex = threading.Lock()

    handler = protocol.Handler(conn=empty_device())
    conn = FakeSocket()
    server.handle_connection(conn, handler, mutex)

    msg = bytearray([protocol.msg_code('SSH_AGENTC_REQUEST_RSA_IDENTITIES')])
    conn = FakeSocket(util.frame(msg))
    server.handle_connection(conn, handler, mutex)
    assert conn.tx.getvalue() == b'\x00\x00\x00\x05\x02\x00\x00\x00\x00'

    msg = bytearray([protocol.msg_code('SSH2_AGENTC_REQUEST_IDENTITIES')])
    conn = FakeSocket(util.frame(msg))
    server.handle_connection(conn, handler, mutex)
    assert conn.tx.getvalue() == b'\x00\x00\x00\x05\x0C\x00\x00\x00\x00'

    msg = bytearray([protocol.msg_code('SSH2_AGENTC_ADD_IDENTITY')])
    conn = FakeSocket(util.frame(msg))
    server.handle_connection(conn, handler, mutex)
    conn.tx.seek(0)
    reply = util.read_frame(conn.tx)
    assert reply == util.pack('B', protocol.msg_code('SSH_AGENT_FAILURE'))

    conn_mock = mock.Mock(spec=FakeSocket)
    conn_mock.recv.side_effect = [Exception, EOFError]
    server.handle_connection(conn=conn_mock, handler=None, mutex=mutex)


def test_server_thread():
    sock = FakeSocket()
    connections = [sock]
    quit_event = threading.Event()

    class FakeServer:
        def accept(self):
            if not connections:
                raise socket.timeout()
            return connections.pop(), 'address'

        def getsockname(self):
            return 'fake_server'

    def handle_conn(conn):
        assert conn is sock
        quit_event.set()

    server.server_thread(sock=FakeServer(),
                         handle_conn=handle_conn,
                         quit_event=quit_event)
    quit_event.wait()


def test_spawn():
    obj = []

    def thread(x):
        obj.append(x)

    with server.spawn(thread, {'x': 1}):
        pass

    assert obj == [1]


def test_run():
    assert server.run_process(['true'], environ={}) == 0
    assert server.run_process(['false'], environ={}) == 1
    assert server.run_process(command=['bash', '-c', 'exit $X'],
                              environ={'X': '42'}) == 42

    with pytest.raises(OSError):
        server.run_process([''], environ={})


def test_remove():
    path = 'foo.bar'

    def remove(p):
        assert p == path

    server.remove_file(path, remove=remove)

    def remove_raise(_):
        raise OSError('boom')

    server.remove_file(path, remove=remove_raise, exists=lambda _: False)

    with pytest.raises(OSError):
        server.remove_file(path, remove=remove_raise, exists=lambda _: True)
