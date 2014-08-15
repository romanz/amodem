from amodem import wave
import subprocess as sp
import signal


def test_launch():
    p = wave.launch('cat', stdin=sp.PIPE)
    p.stdin.close()
    assert p.wait() == 0

    p = wave.launch('bash', stdin=sp.PIPE)
    p.stdin.write(b'exit 42')
    p.stdin.close()
    assert p.wait() == 42

    p = wave.launch('cat', stdin=sp.PIPE, stdout=sp.PIPE)
    s = b'Hello World!'
    p.stdin.write(s)
    p.stdin.flush()
    assert p.stdout.read(len(s)) == s

    p.kill()
    assert p.wait() == -signal.SIGKILL
