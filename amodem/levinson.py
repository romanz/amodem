import numpy as np


def solver(t, y):
    """ Solve Mx = y for x, where M[i,j] = t[|i-j|], in O(N^2) steps.
        See http://en.wikipedia.org/wiki/Levinson_recursion for details.
    """
    N = len(t)
    assert len(y) == N

    t0 = np.array([1.0 / t[0]])
    f = [t0]  # forward vectors
    b = [t0]  # backward vectors
    for n in range(1, N):
        prev_f = f[-1]
        prev_b = b[-1]
        ef = sum(t[n-i] * prev_f[i] for i in range(n))
        eb = sum(t[i+1] * prev_b[i] for i in range(n))
        f_ = np.concatenate([prev_f, [0]])
        b_ = np.concatenate([[0], prev_b])
        det = 1.0 - ef * eb
        f.append((f_ - ef * b_) / det)
        b.append((b_ - eb * f_) / det)

    x = []
    for n in range(N):
        x = np.concatenate([x, [0]])
        ef = sum(t[n-i] * x[i] for i in range(n))
        x = x + (y[n] - ef) * b[n]
    return x
