"""Code which adds Linux ALSA support for interfaces,
recording and playing.

"""

import subprocess
import logging

log = logging.getLogger(__name__)


class Interface:

    RECORDER = 'arecord'
    PLAYER = 'aplay'

    def __init__(self, config):
        self.config = config
        rate = int(config.Fs)
        bits_per_sample = config.bits_per_sample
        assert bits_per_sample == 16

        args = '-f S{0:d}_LE -c 1 -r {1:d} -T 100 -q -'
        args = args.format(bits_per_sample, rate).split()

        self.record_cmd = [self.RECORDER] + args
        self.play_cmd = [self.PLAYER] + args
        self.processes = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        for p in self.processes:
            try:
                p.wait()
            except OSError:
                log.warning('%s failed', p)

    def launch(self, **kwargs):
        log.debug('Launching subprocess: %s', kwargs)
        p = subprocess.Popen(**kwargs)
        self.processes.append(p)
        return p

    def recorder(self):
        return Recorder(self)

    def player(self):
        return Player(self)


class Recorder:
    def __init__(self, lib):
        self.p = lib.launch(args=lib.record_cmd, stdout=subprocess.PIPE)
        self.read = self.p.stdout.read
        self.bufsize = 4096

    def close(self):
        self.p.kill()


class Player:
    def __init__(self, lib):
        self.p = lib.launch(args=lib.play_cmd, stdin=subprocess.PIPE)
        self.write = self.p.stdin.write

    def close(self):
        self.p.stdin.close()
        self.p.wait()
