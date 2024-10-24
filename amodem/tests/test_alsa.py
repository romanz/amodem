import mock

from .. import alsa, config


def test_alsa():
    interface = alsa.Interface(config=config.fastest())
    interface.launch = mock.Mock()
    with interface:
        r = interface.recorder()
        r.read(2)
        r.close()

    p = mock.call(
        args='arecord -f S16_LE -c 1 -r 32000 -T 100 -q -'.split(),
        stdout=-1)
    assert interface.launch.mock_calls == [p, p.stdout.read(2), p.kill()]

    interface.launch = mock.Mock()
    with interface:
        p = interface.player()
        p.write('\x00\x00')
        p.close()

    p = mock.call(
        args='aplay -f S16_LE -c 1 -r 32000 -T 100 -q -'.split(),
        stdin=-1)
    assert interface.launch.mock_calls == [
        p, p.stdin.write('\x00\x00'), p.stdin.close(), p.wait()
    ]


def test_alsa_subprocess():
    interface = alsa.Interface(config=config.fastest())
    with mock.patch('subprocess.Popen') as popen:
        with interface:
            p = interface.launch(args=['foobar'])
            p.wait.side_effect = OSError('invalid command')
            assert interface.processes == [p]
            assert popen.mock_calls == [mock.call(args=['foobar'])]
