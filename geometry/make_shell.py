#!/usr/bin/env python3
"""Генератор геометрии «Раковина» (этап A).
Использование:
    python3 make_shell.py                    # полная модель по ../params.yaml
    python3 make_shell.py --control          # контроль: без рёбер
    python3 make_shell.py --set beta_deg=60 --set N=8 --name test
Выход: geometry/out/<name>.stl, <name>_report.json, <name>_xy.png, <name>_xz.png
Единицы: метры. Ось z вертикальна, начало в центре сферы.
"""
import argparse, json, os, sys
from functools import reduce
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = dict(R_s=0.50, R_o=0.45, R_c=0.10, N=12, beta_deg=65.0,
                rib_thickness=0.010, slit_width=0.02, wave_A=0.0, wave_lambda=0.1,
                shell_t=0.010, tube_t=0.010, plate_t=0.020, spoke_w=0.010,
                seg=96, pts=240, plug_deg=0.0, tube=0)


def load_params(path):
    p = dict(DEFAULTS)
    try:
        import yaml
        with open(path) as f:
            p.update(yaml.safe_load(f) or {})
    except Exception as e:
        print("params.yaml не прочитан, беру значения по умолчанию:", e)
    return p


def rib_polygon(p, phi0):
    """Замкнутый 2D-контур ребра: логарифмическая спираль r=R_o*exp(-k*psi)
    со смещением +-t/2 по нормали и (опционально) волной по нормали."""
    Ro, Rc, tc = p["R_o"], p["R_c"], p["tube_t"]
    t = p["rib_thickness"]
    k = 1.0 / np.tan(np.radians(p["beta_deg"]))
    r_end = Rc + tc * 0.5
    psi0 = -0.06                                   # небольшой вылет за R_o, потом обрезаем
    psi1 = np.log(Ro / r_end) / k
    psi = np.linspace(psi0, psi1, int(p["pts"]))
    r = Ro * np.exp(-k * psi)
    ph = phi0 + psi
    x, y = r * np.cos(ph), r * np.sin(ph)
    dx, dy = np.gradient(x), np.gradient(y)
    ds = np.hypot(dx, dy)
    tx, ty = dx / ds, dy / ds
    nx, ny = -ty, tx
    if p["wave_A"] > 0:
        s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
        w = p["wave_A"] * np.sin(2 * np.pi * s / p["wave_lambda"])
        x, y = x + w * nx, y + w * ny
        dx, dy = np.gradient(x), np.gradient(y)
        ds = np.hypot(dx, dy)
        nx, ny = -dy / ds, dx / ds
    h = t / 2
    left = np.column_stack([x + h * nx, y + h * ny])
    right = np.column_stack([x - h * nx, y - h * ny])
    poly = np.vstack([left, right[::-1]])
    area = 0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1])
    if area < 0:
        poly = poly[::-1]
    return poly


def build(p, control=False):
    Rs, Ro, Rc = p["R_s"], p["R_o"], p["R_c"]
    ts, tc, tp = p["shell_t"], p["tube_t"], p["plate_t"]
    seg, H = int(p["seg"]), 2.4 * Rs
    cyl = lambda r, h=H: Manifold.cylinder(h, r, r, seg, True)

    sph_out = Manifold.sphere(Rs + ts / 2, seg)
    sph_in = Manifold.sphere(Rs - ts / 2, seg)
    annulus = cyl(Ro) - cyl(Rc)
    caps = (sph_out - sph_in) ^ annulus                       # крыша и пол

    tube = (cyl(Rc + tc) - cyl(Rc)) ^ sph_out                 # стенка центрального цилиндра

    zb = -np.sqrt(Rs ** 2 - Rc ** 2)                          # плита закрывает дно цилиндра
    plate = cyl(Rc + tc / 2, tp).translate((0, 0, zb))
    spokes = Manifold.cube((2 * (Rc + tc), p["spoke_w"], 4 * tp), True)
    spokes = spokes + spokes.rotate((0, 0, 90))
    slit = (cyl(Rc, 4 * tp) - cyl(Rc - p["slit_width"], 4 * tp)) - spokes
    plate = plate - slit.translate((0, 0, zb))

    parts = [caps, plate] + ([tube] if p.get("tube", 0) else [])
    if p.get("plug_deg", 0) > 0:
        a_ = np.radians(p["plug_deg"])
        ang = np.linspace(-a_, a_, 24)
        poly = np.vstack([[0, 0], np.column_stack([2 * Ro * np.cos(ang), 2 * Ro * np.sin(ang)])])
        wedge = Manifold.extrude(CrossSection([poly]), H).translate((0, 0, -H / 2))
        parts.append(((cyl(Ro) - cyl(Ro - 0.012)) ^ wedge) ^ sph_out)
    if not control:
        sph = Manifold.sphere(Rs, seg)
        clip = cyl(Ro)
        for i in range(int(p["N"])):
            poly = rib_polygon(p, 2 * np.pi * i / p["N"])
            rib = Manifold.extrude(CrossSection([poly]), H).translate((0, 0, -H / 2))
            parts.append((rib ^ sph) ^ clip)
    return reduce(lambda a, b: a + b, parts)


def to_trimesh(m):
    me = m.to_mesh()
    return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)


def save_sections(tm, base):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        for name, normal, (a, b) in (("xy", [0, 0, 1], (0, 1)), ("xz", [0, 1, 0], (0, 2))):
            sec = tm.section(plane_origin=[0, 0, 0], plane_normal=normal)
            fig, ax = plt.subplots(figsize=(6, 6))
            if sec is not None:
                for seg_ in sec.discrete:
                    ax.plot(seg_[:, a], seg_[:, b], "b", lw=0.7)
            ax.set_aspect("equal")
            ax.set_title(name.upper())
            fig.savefig(f"{base}_{name}.png", dpi=130)
            plt.close(fig)
    except Exception as e:
        print("Картинки сечений не построены:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default=os.path.join(HERE, "..", "params.yaml"))
    ap.add_argument("--set", action="append", default=[], help="key=value")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--name", default=None)
    a = ap.parse_args()
    p = load_params(a.params)
    for kv in a.set:
        k, v = kv.split("=", 1)
        p[k] = type(DEFAULTS.get(k, 1.0))(float(v)) if k not in ("N", "seg", "pts") else int(float(v))
    name = a.name or ("control" if a.control else "shell")
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, name)

    m = build(p, a.control)
    tm = to_trimesh(m)
    tm.export(base + ".stl")

    rep = dict(name=name, params=p, control=a.control,
               watertight=bool(tm.is_watertight), winding_consistent=bool(tm.is_winding_consistent),
               volume_m3=float(tm.volume), bodies=int(tm.body_count),
               faces=int(len(tm.faces)), bounds=tm.bounds.tolist())
    if not a.control and p["N"] > 1:
        rot = m.rotate((0, 0, 360.0 / p["N"]))
        inter = to_trimesh(rot ^ m)
        rep["symmetry_overlap"] = float(inter.volume / tm.volume)   # ожидаем ~1.0
    with open(base + "_report.json", "w") as f:
        json.dump(rep, f, indent=2)
    save_sections(tm, base)
    print(json.dumps({k: v for k, v in rep.items() if k != "params"}, indent=2))
    ok = rep["watertight"] and rep["bodies"] == 1 and rep["volume_m3"] > 0
    print("ПРОВЕРКА:", "OK" if ok else "ЕСТЬ ПРОБЛЕМЫ")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
