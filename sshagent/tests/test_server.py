import tempfile
import socket
import os
import io
import pytest

from .. import server
from .. import protocol
from .. import util


def test_socket():
    path = tempfile.mktemp()
    with server.unix_domain_socket_server(path):
        pass
    assert not os.path.isfile(path)


class SocketMock(object):

    def __init__(self, data=b''):
        self.rx = io.BytesIO(data)
        self.tx = io.BytesIO()

    def sendall(self, data):
        self.tx.write(data)

    def recv(self, size):
        return self.rx.read(size)

    def close(self):
        pass


def test_handle():
    handler = protocol.Handler(keys=[], signer=None)
    conn = SocketMock()
    server.handle_connection(conn, handler)

    msg = bytearray([protocol.SSH_AGENTC_REQUEST_RSA_IDENTITIES])
    conn = SocketMock(util.frame(msg))
    server.handle_connection(conn, handler)
    assert conn.tx.getvalue() == b'\x00\x00\x00\x05\x02\x00\x00\x00\x00'

    msg = bytearray([protocol.SSH2_AGENTC_REQUEST_IDENTITIES])
    conn = SocketMock(util.frame(msg))
    server.handle_connection(conn, handler)
    assert conn.tx.getvalue() == b'\x00\x00\x00\x05\x0C\x00\x00\x00\x00'


class ServerMock(object):

    def __init__(self, connections, name):
        self.connections = connections
        self.name = name

    def getsockname(self):
        return self.name

    def accept(self):
        if self.connections:
            return self.connections.pop(), 'address'
        raise socket.error('stop')


def test_server_thread():
    s = ServerMock(connections=[SocketMock()], name='mock')
    h = protocol.Handler(keys=[], signer=None)
    server.server_thread(s, h)


def test_spawn():
    obj = []

    def thread(x):
        obj.append(x)

    with server.spawn(thread, x=1):
        pass

    assert obj == [1]


def test_run():
    assert server.run_process(['true'], environ={}) == 0
    assert server.run_process(['false'], environ={}) == 1
    assert server.run_process(
        command='exit $X',
        environ={'X': '42'},
        use_shell=True) == 42

    with pytest.raises(OSError):
        server.run_process([''], environ={})


def test_serve_main():
    with server.serve(public_keys=[], signer=None, sock_path=None):
        pass
