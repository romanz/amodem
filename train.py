import itertools

prefix = [1]*400 + [0]*50


def _equalizer_sequence():
    res = []

    symbols = [1, 1j, -1, -1j]
    for s in itertools.islice(itertools.cycle(symbols), 100):
        res.extend([s]*1 + [0]*1)

    res.extend([0]*20)
    return res

equalizer = _equalizer_sequence()
