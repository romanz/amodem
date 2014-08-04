import numpy as np

def points(minR, maxR):
    minR = float(minR)
    maxR = float(maxR)
    n = int(maxR)
    I = range(-n, n+1)
    P = [x + 1.0j*y for x in I for y in I]
    P = np.array([p for p in P if (minR <= abs(p) and abs(p) <= maxR)])
    return P / maxR

if __name__ == '__main__':
    import pylab
    import sys
    r, R = sys.argv[1:]
    p = points(r, R)
    pylab.plot(p.real, p.imag, '.')
    pylab.title(str(len(p)))
    c = np.exp(2j*np.pi*np.linspace(0, 1, 1000))
    pylab.plot(c.real, c.imag, ':')
    pylab.grid('on')
    pylab.axis('equal')
    pylab.show()

