import socket
import os
import subprocess
import tempfile
import contextlib
import threading
import logging
log = logging.getLogger(__name__)

from . import protocol
from . import formats
from . import util

@contextlib.contextmanager
def unix_domain_socket_server(sock_path):
    log.debug('serving on SSH_AUTH_SOCK=%s', sock_path)
    try:
        os.remove(sock_path)
    except OSError:
        if os.path.exists(sock_path):
            raise

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)
    try:
        yield server
    finally:
        os.remove(sock_path)

def handle_connection(conn, keys, signer):
    try:
        log.debug('welcome agent')
        while True:
            msg = util.read_frame(conn)
            reply = protocol.handle_message(msg=msg, keys=keys, signer=signer)
            util.send(conn, reply)
    except EOFError:
        log.debug('goodbye agent')
    except:
        log.exception('error')
        raise

def server_thread(server, keys, signer):
    log.debug('server thread started')
    while True:
        log.debug('waiting for connection on %s', server.getsockname())
        try:
            conn, _ = server.accept()
        except socket.error as e:
            log.debug('server error: %s', e, exc_info=True)
            break
        with contextlib.closing(conn):
            handle_connection(conn, keys, signer)
    log.debug('server thread stopped')


@contextlib.contextmanager
def spawn(func, **kwargs):
    t = threading.Thread(target=func, kwargs=kwargs)
    t.start()
    yield
    t.join()


def run(command, environ):
    log.debug('running %r with %r', command, environ)
    env = dict(os.environ)
    env.update(environ)
    try:
        p = subprocess.Popen(args=command, env=env)
    except OSError as e:
        raise OSError('cannot run %r: %s' % (command, e))
    log.debug('subprocess %d is running', p.pid)
    ret = p.wait()
    log.debug('subprocess %d exited: %d', p.pid, ret)
    return ret


def serve(key_files, command, signer, sock_path=None):
    if sock_path is None:
        sock_path = tempfile.mktemp(prefix='ssh-agent-')

    keys = [formats.parse_public_key(k) for k in key_files]
    environ = {'SSH_AUTH_SOCK': sock_path, 'SSH_AGENT_PID': str(os.getpid())}
    with unix_domain_socket_server(sock_path) as server:
        with spawn(server_thread, server=server, keys=keys, signer=signer):
            try:
                ret = run(command=command, environ=environ)
            finally:
                log.debug('closing server')
                server.shutdown(socket.SHUT_RD)
    return ret
