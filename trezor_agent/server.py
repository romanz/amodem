import contextlib
import logging
import os
import socket
import subprocess
import tempfile
import threading

from . import util

log = logging.getLogger(__name__)

UNIX_SOCKET_TIMEOUT = 0.1


def remove_file(path, remove=os.remove, exists=os.path.exists):
    try:
        remove(path)
    except OSError:
        if exists(path):
            raise


@contextlib.contextmanager
def unix_domain_socket_server(sock_path):
    log.debug('serving on SSH_AUTH_SOCK=%s', sock_path)
    remove_file(sock_path)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)
    try:
        yield server
    finally:
        remove_file(sock_path)


def handle_connection(conn, handler):
    try:
        log.debug('welcome agent')
        while True:
            msg = util.read_frame(conn)
            reply = handler.handle(msg=msg)
            util.send(conn, reply)
    except EOFError:
        log.debug('goodbye agent')
    except Exception as e:  # pylint: disable=broad-except
        log.warning('error: %s', e, exc_info=True)


def retry(func, exception_type, quit_event):
    while True:
        if quit_event.is_set():
            raise StopIteration
        try:
            return func()
        except exception_type:
            pass


def server_thread(server, handler, quit_event):
    log.debug('server thread started')

    def accept_connection():
        conn, _ = server.accept()
        conn.settimeout(None)
        return conn

    while True:
        log.debug('waiting for connection on %s', server.getsockname())
        try:
            conn = retry(accept_connection, socket.timeout, quit_event)
        except StopIteration:
            log.debug('server stopped')
            break
        with contextlib.closing(conn):
            handle_connection(conn, handler)
    log.debug('server thread stopped')


@contextlib.contextmanager
def spawn(func, kwargs):
    t = threading.Thread(target=func, kwargs=kwargs)
    t.start()
    yield
    t.join()


@contextlib.contextmanager
def serve(handler, sock_path=None, timeout=UNIX_SOCKET_TIMEOUT):
    if sock_path is None:
        sock_path = tempfile.mktemp(prefix='ssh-agent-')

    environ = {'SSH_AUTH_SOCK': sock_path, 'SSH_AGENT_PID': str(os.getpid())}
    with unix_domain_socket_server(sock_path) as server:
        server.settimeout(timeout)
        quit_event = threading.Event()
        kwargs = dict(server=server, handler=handler, quit_event=quit_event)
        with spawn(server_thread, kwargs):
            try:
                yield environ
            finally:
                log.debug('closing server')
                quit_event.set()


def run_process(command, environ, use_shell=False):
    log.info('running %r with %r', command, environ)
    env = dict(os.environ)
    env.update(environ)
    try:
        p = subprocess.Popen(args=command, env=env, shell=use_shell)
    except OSError as e:
        raise OSError('cannot run %r: %s' % (command, e))
    log.debug('subprocess %d is running', p.pid)
    ret = p.wait()
    log.debug('subprocess %d exited: %d', p.pid, ret)
    return ret
