#!/usr/bin/env python3
"""Генератор геометрии «Раковина» v2.
Новое: коническая центральная полость (cone_top/cone_bot) и расширенная волна рёбер
(wave_A, wave_lambda, wave_grow, wave_skew, wave_phase).
Использование:
    python3 make_shell.py                                  # по ../params.yaml
    python3 make_shell.py --control
    python3 make_shell.py --set cone_top=0.12 --set cone_bot=0.07 --name cone1
    python3 make_shell.py --set wave_A=0.006 --set wave_lambda=0.12 --name wave1
Выход: geometry/out/<name>.stl (ASCII не нужен: make_case.py сам пишет именованный STL),
       <name>_report.json, <name>_xy.png, <name>_xz.png. Единицы: метры, z вертикально.
cone_top/cone_bot = 0 означает «взять R_c» (прежний цилиндр).
"""
import argparse, json, os, sys
from functools import reduce
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = dict(R_s=0.50, R_o=0.45, R_c=0.10, N=12, beta_deg=65.0,
                rib_thickness=0.010, slit_width=0.02, wave_A=0.0, wave_lambda=0.1,
                wave_grow=0.0, wave_skew=0.0, wave_phase=0.0,
                shell_t=0.010, tube_t=0.010, plate_t=0.020, spoke_w=0.010,
                seg=96, pts=240, plug_deg=0.0, tube=0, cone_top=0.0, cone_bot=0.0)


def load_params(path):
    p = dict(DEFAULTS)
    try:
        import yaml
        with open(path) as f:
            p.update(yaml.safe_load(f) or {})
    except Exception as e:
        print("params.yaml не прочитан, беру значения по умолчанию:", e)
    return p


def radii(p):
    rt = p["cone_top"] or p["R_c"]
    rb = p["cone_bot"] or p["R_c"]
    return float(rt), float(rb)


def rib_polygon(p, phi0):
    """2D-контур ребра: логарифмическая спираль r=R_o*exp(-k*psi), смещение +-t/2 по нормали,
    волна по нормали: w(s) = A*(1+grow*s/L) * [sin(x) + skew*sin(2x)/2], x = 2*pi*s/lambda + phase."""
    Ro = p["R_o"]
    rt, rb = radii(p)
    t = p["rib_thickness"]
    k = 1.0 / np.tan(np.radians(p["beta_deg"]))
    r_end = max(rb - 0.005, 0.02)
    psi = np.linspace(-0.06, np.log(Ro / r_end) / k, int(p["pts"]))
    r = Ro * np.exp(-k * psi)
    ph = phi0 + psi
    x, y = r * np.cos(ph), r * np.sin(ph)
    if p["wave_A"] > 0:
        dx, dy = np.gradient(x), np.gradient(y)
        ds = np.hypot(dx, dy)
        nx, ny = -dy / ds, dx / ds
        s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
        u = 2 * np.pi * s / p["wave_lambda"] + p["wave_phase"]
        amp = p["wave_A"] * (1 + p["wave_grow"] * s / s[-1])
        w = amp * (np.sin(u) + p["wave_skew"] * 0.5 * np.sin(2 * u))
        w *= np.clip(s / 0.05, 0, 1)                      # плавный вход без волны на самой кромке
        x, y = x + w * nx, y + w * ny
    dx, dy = np.gradient(x), np.gradient(y)
    ds = np.hypot(dx, dy)
    nx, ny = -dy / ds, dx / ds
    h = t / 2
    left = np.column_stack([x + h * nx, y + h * ny])
    right = np.column_stack([x - h * nx, y - h * ny])
    poly = np.vstack([left, right[::-1]])
    area = 0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1])
    return poly if area > 0 else poly[::-1]


def min_gap_estimate(p):
    """Оценка зазора между соседними рёбрами (без волны) у горла нижнего радиуса."""
    rt, rb = radii(p)
    b = np.radians(p["beta_deg"])
    g = lambda r: (2 * np.pi * r / p["N"]) * np.cos(b) - p["rib_thickness"]
    return g(p["R_o"]), g(rt), g(rb)


def build(p, control=False):
    Rs, Ro, Rc = p["R_s"], p["R_o"], p["R_c"]
    rt, rb = radii(p)
    ts, tc, tp = p["shell_t"], p["tube_t"], p["plate_t"]
    seg, H = int(p["seg"]), 2.4 * Rs
    cyl = lambda r, h=H: Manifold.cylinder(h, r, r, seg, True)

    sl = (rt - rb) / 1.0                                     # конус: радиус rb при z=-0.5, rt при z=+0.5
    cone = Manifold.cylinder(1.1, rb - 0.05 * sl, rt + 0.05 * sl, seg, True)

    sph_out = Manifold.sphere(Rs + ts / 2, seg)
    sph_in = Manifold.sphere(Rs - ts / 2, seg)
    caps = (sph_out - sph_in) ^ (cyl(Ro) - cone)             # крыша и пол с коническим отверстием

    zb = -np.sqrt(Rs ** 2 - rb ** 2)                          # плита закрывает дно полости
    plate = cyl(rb + 0.01, tp).translate((0, 0, zb))
    w_ = min(p["slit_width"], 0.5 * rb)
    spokes = Manifold.cube((2 * (rb + 0.02), p["spoke_w"], 4 * tp), True)
    spokes = spokes + spokes.rotate((0, 0, 90))
    slit = (cyl(rb, 4 * tp) - cyl(rb - w_, 4 * tp)) - spokes
    plate = plate - slit.translate((0, 0, zb))

    parts = [caps, plate]
    if p.get("tube", 0):
        parts.append((cyl(Rc + tc) - cyl(Rc)) ^ sph_out)
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
            parts.append(((rib ^ sph) ^ clip) - cone)        # кромки рёбер подрезаны по конусу
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
        p[k] = int(float(v)) if k in ("N", "seg", "pts", "tube") else float(v)
    gi, gt, gb = min_gap_estimate(p)
    print(f"Оценка зазора между рёбрами: вход {gi*1000:.1f} мм, верх полости {gt*1000:.1f} мм, низ полости {gb*1000:.1f} мм")
    if gb < 0.003 or gt < 0.003:
        print("ПРЕДУПРЕЖДЕНИЕ: зазор у горла < 3 мм - уменьшите rib_thickness/beta_deg/N или увеличьте cone_bot.")
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
        rep["symmetry_overlap"] = float(to_trimesh(rot ^ m).volume / tm.volume)
    with open(base + "_report.json", "w") as f:
        json.dump(rep, f, indent=2)
    save_sections(tm, base)
    print(json.dumps({k: v for k, v in rep.items() if k != "params"}, indent=2))
    ok = rep["watertight"] and rep["bodies"] == 1 and rep["volume_m3"] > 0
    print("ПРОВЕРКА:", "OK" if ok else "ЕСТЬ ПРОБЛЕМЫ")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
