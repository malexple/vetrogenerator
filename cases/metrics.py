#!/usr/bin/env python3
"""Этап C: метрики закрутки внутри центрального цилиндра по расчёту в processor*.
Подготовка (один раз на расчёт):
    cd cases/t1
    mpirun --allow-run-as-root -np 8 foamPostProcess -parallel -func writeCellCentres -latestTime
    mpirun --allow-run-as-root -np 8 foamPostProcess -parallel -func writeCellVolumes -latestTime
Запуск:
    python3 metrics.py --case ../cases/t1 --vinf 3.5 [--append ../results/summary.csv]
Метрики считаются при r < R_c и |z| < zmax (ось цилиндра = ось z, вихрь против часовой стрелки > 0).
"""
import argparse, csv, glob, json, os, re
import numpy as np


def read_field(path):
    t = open(path).read()
    m = re.search(r"internalField\s+(uniform|nonuniform)\s*(List<(\w+)>)?\s*(\d+)?\s*", t)
    if m.group(1) == "uniform":
        v = np.fromstring(t[m.end():t.index(";", m.end())].replace("(", " ").replace(")", " "), sep=" ")
        return v, True
    kind, n = m.group(3), int(m.group(4))
    start = t.index("(", m.end() - 1) + 1
    end = t.index("\n)\n;", start)
    a = np.fromstring(t[start:end].replace("(", " ").replace(")", " "), sep=" ")
    return (a.reshape(n, 3) if kind == "vector" else a), False


def latest_time(case):
    ts = []
    for d in glob.glob(os.path.join(case, "processor0", "*")):
        b = os.path.basename(d)
        try:
            ts.append((float(b), b))
        except ValueError:
            pass
    return max(ts)[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--vinf", type=float, required=True)
    ap.add_argument("--time", default=None)
    ap.add_argument("--Rc", type=float, default=0.10)
    ap.add_argument("--zmax", type=float, default=0.45)
    ap.add_argument("--slab", type=float, default=0.10, help="полутолщина слоя вокруг z=0 для числа закрутки")
    ap.add_argument("--append", default=None)
    a = ap.parse_args()
    tm = a.time or latest_time(a.case)
    X, U, V = [], [], []
    for pd in sorted(glob.glob(os.path.join(a.case, "processor*"))):
        d = os.path.join(pd, tm)
        c, _ = read_field(os.path.join(d, "C"))
        u, uni = read_field(os.path.join(d, "U"))
        v, _ = read_field(os.path.join(d, "V"))
        X.append(c.reshape(-1, 3)); U.append(u.reshape(-1, 3)); V.append(np.atleast_1d(v))
    X, U, V = np.vstack(X), np.vstack(U), np.concatenate(V)
    r = np.hypot(X[:, 0], X[:, 1])
    sel = (r < a.Rc) & (np.abs(X[:, 2]) < a.zmax) & (r > 1e-6)
    x, y, z, ux, uy, uz, vol, rr = X[sel, 0], X[sel, 1], X[sel, 2], U[sel, 0], U[sel, 1], U[sel, 2], V[sel], r[sel]
    vt = (-y * ux + x * uy) / rr
    w = vol / vol.sum()
    res = dict(case=os.path.basename(os.path.abspath(a.case)), time=tm, vinf=a.vinf, cells_in_cylinder=int(sel.sum()),
               vtheta_mean=float((vt * w).sum() / a.vinf),
               vtheta_abs_mean=float((np.abs(vt) * w).sum() / a.vinf),
               vtheta_max=float(vt.max() / a.vinf), vtheta_min=float(vt.min() / a.vinf),
               vz_mean=float((uz * w).sum() / a.vinf),
               speed_max=float(np.sqrt(ux**2 + uy**2 + uz**2).max() / a.vinf))
    sl = np.abs(z) < a.slab
    if sl.sum() > 0:
        num = (vt[sl] * uz[sl] * rr[sl] * vol[sl]).sum()
        den = a.Rc * (uz[sl] ** 2 * vol[sl]).sum()
        res["swirl_number_S"] = float(num / den) if den > 0 else None
    print(json.dumps(res, indent=2))
    if a.append:
        new = not os.path.exists(a.append)
        with open(a.append, "a", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(res.keys()))
            if new:
                wr.writeheader()
            wr.writerow(res)


if __name__ == "__main__":
    main()
