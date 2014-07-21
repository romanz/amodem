import stream
import wave


def test():
    p = wave.record('-', stdout=wave.sp.PIPE)
    f = stream.FileBuffer(p.stdout)

    result = zip(range(10), f)
    p.stop()

    j = 0
    for i, buf in result:
        assert i == j
        assert len(buf) == f.SAMPLES
        j += 1

    try:
        for buf in f:
            pass
    except IOError as e:
        assert str(e) == 'timeout'
