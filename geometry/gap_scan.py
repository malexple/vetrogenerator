import numpy as np
Rs, Ro, Rc = 0.50, 0.45, 0.10
h = lambda r: 2*np.sqrt(Rs**2 - r**2)

def gaps(N, beta_deg, t):
    b = np.radians(beta_deg)
    g = lambda r: (2*np.pi*r/N)*np.cos(b) - t
    return g(Ro), g(Rc)

print("N beta t_mm gap_in_mm gap_throat_mm A_in A_throat ratio")
for N in (8, 12, 16):
    for beta in (55, 65, 70, 75):
        for t in (0.005, 0.010, 0.015):
            gi, gt = gaps(N, beta, t)
            Ai = N*max(gi, 0)*h(Ro); At = N*max(gt, 0)*h(Rc)
            ratio = Ai/At if At > 0 else float("nan")
            print(N, beta, int(t*1000), round(gi*1000, 1), round(gt*1000, 1), round(Ai, 3), round(At, 3), round(ratio, 1))
