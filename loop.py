import numpy as np

class Filter(object):
    def __init__(self, b, a=()):
        self.b = b
        self.a = a
        self.x = [0] * len(b)
        self.y = [0] * len(a)

    def __call__(self, x):
        self.x = [x] + self.x
        self.x = self.x[:len(self.b)]
        self.y = self.y[:len(self.a)]
        y = np.dot(self.x, self.b) + np.dot(self.y, self.a)
        self.y = [y] + self.y
        return y

class Loop(object):
    def __init__(self, x, A, k, h):
        self.x = np.array(x)
        self.A = np.array(A)
        self.k = np.array(k)
        self.h = np.array(h)

    def __call__(self, y):
        self.err = y - np.dot(self.h, self.x)
        self.dx = self.k * self.err
        self.x = self.x + self.dx
        self.x = np.dot(self.A, self.x)

class Integrator(Loop):
    def __init__(self, phase, freq, k):
        x = [phase, freq]  # state variable vector
        # evolution matrix:
        # | phase' = phase + freq
        # | freq' = freq
        A = [[1, 1], [0, 1]]
        h = [1, 0]  # phase = dot(h, x)
        Loop.__init__(self, x=x, A=A, k=k, h=h)

