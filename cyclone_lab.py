#!/usr/bin/env python3
"""
cyclone_lab.py — экспериментальный циклон Ø100×300 для пылевой плазмы.
Тангенциальный вход 50x20, конус + бункер для железного порошка,
верхний выход Ø30, радиальные порты под вольфрамовые электроды Ø2.

Зависимости: manifold3d, trimesh, numpy  (matplotlib — только для превью)
Запуск:   python3 cyclone_lab.py            -> cyclone_lab.stl
          python3 cyclone_lab.py --preview  -> + cyclone_lab_preview.png
Все размеры в миллиметрах.
"""

import sys
import numpy as np
import trimesh
import math
from manifold3d import Manifold

# ----------------------------- параметры -----------------------------
P = dict(
    D_body        = 100.0,   # Ø цилиндрической части
    H_body        = 300.0,   # высота цилиндра
    wall          = 2.5,     # толщина стенки под печать

    # нижний конус и бункер для порошка
    cone_H        = 60.0,    # высота конуса (Ø тела -> Ø низа)
    D_cone_bottom = 30.0,    # Ø нижнего отверстия конуса
    bin_H         = 25.0,    # цилиндрический бункер под конусом (0 = выкл)

    # верхний выход
    D_outlet      = 30.0,
    H_outlet      = 40.0,

    # тангенциальный вход: слот 50 (вертикаль) x 20 (проникновение внутрь),
    # канал идёт по касательной (вдоль Y), патрубок наружу 35
    inlet_depth   = 20.0,    # насколько заходит в камеру (по радиусу)
    inlet_slot_V  = 50.0,    # вертикальный размер слота
    inlet_tangent = 50.0,    # длина слота по касательной
    inlet_len_out = 35.0,    # патрубок наружу
    inlet_z       = 260.0,   # высота центра входа

    # радиальные порты под электроды (стержни Ø2)
    rod_d         = 2.0,
    clearance     = 0.5,     # зазор на сторону
    rod_z         = (150.0, 200.0),   # высоты портов
    rod_deg       = (0.0, 180.0),     # азимуты

    N             = 128,     # сегментов на окружности
)

OUT_STL = "cyclone_lab.stl"


# ----------------------------- примитивы -----------------------------
def ring_z(r_out, r_in, z0, z1, n):
    """Труба вдоль Z с открытыми торцами (если r_in > 0)."""
    outer = Manifold.cylinder(z1 - z0, r_out, r_out, n).translate((0, 0, z0))
    if r_in <= 0:
        return outer
    inner = Manifold.cylinder((z1 - z0) + 2, r_in, r_in, n).translate((0, 0, z0 - 1))
    return outer - inner


def radial_hole(r_h, z, angle_deg, reach, n):
    hole = Manifold.cylinder(2 * reach, r_h, r_h, n)
    return hole.rotate((0, 90, angle_deg)).translate((0.0, 0.0, z))


# ----------------------------- построение -----------------------------
def build(p):
    R  = p["D_body"] / 2.0
    Rw = R - p["wall"]
    N  = p["N"]

    # --- наружное тело ---
    outer = Manifold.cylinder(p["H_body"], R, R, N)                    # цилиндр
    cone  = Manifold.cylinder(p["cone_H"], p["D_cone_bottom"]/2, R, N) \
        .translate((0, 0, -p["cone_H"]))
    outer += cone
    if p["bin_H"] > 0:
        outer += Manifold.cylinder(p["bin_H"], p["D_cone_bottom"]/2,
                                   p["D_cone_bottom"]/2, N) \
            .translate((0, 0, -p["cone_H"] - p["bin_H"]))
    outer += Manifold.cylinder(p["H_outlet"], p["D_outlet"]/2,
                               p["D_outlet"]/2, N) \
        .translate((0, 0, p["H_body"]))

    # патрубок входа (по касательной, вдоль Y, центр на высоте inlet_z)
    x0, x1 = R - p["inlet_depth"], R + p["inlet_len_out"]
    duct = Manifold.cube([x1 - x0, p["inlet_tangent"], p["inlet_slot_V"]],
                         center=True)
    duct = duct.translate(((x0 + x1) / 2, 0, p["inlet_z"]))
    outer += duct

    # --- внутренняя полость ---
    inner = Manifold.cylinder(p["H_body"] + 2, Rw, Rw, N).translate((0, 0, -1))
    cone_i = Manifold.cylinder(p["cone_H"] + 2,
                               max(p["D_cone_bottom"]/2 - p["wall"], 1.0),
                               Rw, N).translate((0, 0, -p["cone_H"] - 1))
    inner += cone_i
    if p["bin_H"] > 0:
        rbi = max(p["D_cone_bottom"]/2 - p["wall"], 1.0)
        inner += Manifold.cylinder(p["bin_H"] + 2, rbi, rbi, N) \
            .translate((0, 0, -p["cone_H"] - p["bin_H"] - 1))
    r_o = max(p["D_outlet"]/2 - p["wall"], 1.0)
    inner += Manifold.cylinder(p["H_outlet"] + 2, r_o, r_o, N) \
        .translate((0, 0, p["H_body"] - 1))

    # канал входа (чуть шире наружного, чтобы пробить дно патрубка)
    v0, v1 = x0 - 1, x1 + 1
    void = Manifold.cube([v1 - v0, p["inlet_tangent"] - 2 * p["wall"],
                          p["inlet_slot_V"] - 2 * p["wall"]], center=True)
    void = void.translate(((v0 + v1) / 2, 0, p["inlet_z"]))
    inner += void

    # отверстия под электроды
    r_h = p["rod_d"] / 2 + p["clearance"]
    for z, a in zip(p["rod_z"], p["rod_deg"]):
        inner += radial_hole(r_h, z, a, R + 5, N)

    body = outer - inner
    if body.status().name != "NoError":
        raise RuntimeError(f"boolean failed: {body.status()}")
    return body, inner


# ----------------------------- экспорт/контроль -----------------------------
def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=False)


def report(tm, chamber_volume_mm3):
    print(f"вершин/граней : {len(tm.vertices)} / {len(tm.faces)}")
    print(f"герметичность : watertight={tm.is_watertight}, "
          f"winding={tm.is_winding_consistent}, euler={tm.euler_number}")
    print(f"объём детали  : {tm.volume/1000:8.1f} см^3  "
          f"(~{tm.volume/1000*1.24:6.1f} г PETG)")
    print(f"камера (полость): {chamber_volume_mm3/1000:8.1f} см^3")
    b = tm.bounds
    print(f"габариты      : {np.round(b[1]-b[0]).astype(int)} мм")


def preview(tm, zs):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(zs), figsize=(6 * len(zs), 6))
    for ax, z in zip(np.atleast_1d(axes), zs):
        sec = tm.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            continue
        for poly in sec.discrete:
            ax.plot(poly[:, 0], poly[:, 1], lw=0.9)
        ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_title(f"сечение z = {z} мм")
    fig.tight_layout()
    fig.savefig("cyclone_lab_preview.png", dpi=150)
    print("превью: cyclone_lab_preview.png")


if __name__ == "__main__":
    body, inner = build(P)
    tm = to_trimesh(body)
    tm.export(OUT_STL)
    print(f"записан: {OUT_STL}")
    report(tm, inner.volume())
    if "--preview" in sys.argv:
        preview(tm, zs=(150, 262, -40))