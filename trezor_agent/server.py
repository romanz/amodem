"""UNIX-domain socket server for ssh-agent implementation."""
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
    """Remove file, and raise OSError if still exists."""
    try:
        remove(path)
    except OSError:
        if exists(path):
            raise


@contextlib.contextmanager
def unix_domain_socket_server(sock_path):
    """
    Create UNIX-domain socket on specified path.

    Listen on it, and delete it after the generated context is over.
    """
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
    """
    Handle a single connection using the specified protocol handler in a loop.

    Exit when EOFError is raised.
    All other exceptions are logged as warnings.
    """
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
    """
    Run the function, retrying when the specified exception_type occurs.

    Poll quit_event on each iteration, to be responsive to an external
    exit request.
    """
    while True:
        if quit_event.is_set():
            raise StopIteration
        try:
            return func()
        except exception_type:
            pass


def server_thread(sock, handler, quit_event):
    """Run a server on the specified socket."""
    log.debug('server thread started')

    def accept_connection():
        conn, _ = sock.accept()
        conn.settimeout(None)
        return conn

    while True:
        log.debug('waiting for connection on %s', sock.getsockname())
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
    """Spawn a thread, and join it after the context is over."""
    t = threading.Thread(target=func, kwargs=kwargs)
    t.start()
    yield
    t.join()


@contextlib.contextmanager
def serve(handler, sock_path=None, timeout=UNIX_SOCKET_TIMEOUT):
    """
    Start the ssh-agent server on a UNIX-domain socket.

    If no connection is made during the specified timeout,
    retry until the context is over.
    """
    if sock_path is None:
        sock_path = tempfile.mktemp(prefix='ssh-agent-')

    environ = {'SSH_AUTH_SOCK': sock_path, 'SSH_AGENT_PID': str(os.getpid())}
    with unix_domain_socket_server(sock_path) as sock:
        sock.settimeout(timeout)
        quit_event = threading.Event()
        kwargs = dict(sock=sock, handler=handler, quit_event=quit_event)
        with spawn(server_thread, kwargs):
            try:
                yield environ
            finally:
                log.debug('closing server')
                quit_event.set()


def run_process(command, environ):
    """
    Run the specified process and wait until it finishes.

    Use environ dict for environment variables.
    """
    log.info('running %r with %r', command, environ)
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
