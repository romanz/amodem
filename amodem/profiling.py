import cProfile
import contextlib


@contextlib.contextmanager
def save(filename=None):
    if filename:
        pr = cProfile.Profile()
        pr.enable()
        yield
        pr.disable()
        pr.dump_stats(filename)
    else:
        yield
