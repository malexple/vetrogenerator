#!/usr/bin/env python3
"""Генератор STL "циклон + 24 лопастей-полумесяцев + наклонные дверцы-трамплины" (размеры в мм, на выходе в метрах).
Запуск: python make_cyclone_v16.py
"""
import argparse, json, math, os
import numpy as np

# ИСПРАВЛЕНО: Задаем N=24, увеличиваем угол наклона door_angle_deg
# и поднимаем параметр door_lift до 15.0 мм для выраженного винтового эффекта
P = dict(H=300.0, R_bot=28.0, R_top=70.0, R_bulge=160.0, N=24, vane_t=1.8, wall_t=2.0, floor_t=3.0,
         sweep_deg=35.0, macro_twist=1.2, bulge_pow=1.0,
         twist_deg_per_cm=2.0, twist_accel=0.0,
         wave_A=3.0, wave_lambda=40.0, crest_deg=60.0, wave_ramp=20.0, wave_phase_deg=0.0,
         door_h_frac=0.10, door_fill=0.5, door_every=1, door_angle_deg=45.0, door_lift=15.0, door_t=1.5,
         Nz=60, Ns=16, units=1e-3)


def ss(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def thick_sheet(S, th):
    """Замкнутое тело: срединная поверхность S (nu,nv,3) +- th/2 по нормали. Возвращает (вершины, треугольники)."""
    nu, nv, _ = S.shape
    dI, dJ = np.gradient(S, axis=0), np.gradient(S, axis=1)
    N = np.cross(dI, dJ)
    N /= np.maximum(np.linalg.norm(N, axis=2, keepdims=True), 1e-12)
    V = np.vstack([(S - N * th / 2).reshape(-1, 3), (S + N * th / 2).reshape(-1, 3)])
    off = nu * nv
    ix = lambda i, j: i * nv + j
    T = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            a, b, c, d = ix(i, j), ix(i + 1, j), ix(i + 1, j + 1), ix(i, j + 1)
            T += [(a, b, c), (a, c, d)]
            T += [(c + off, b + off, a + off), (d + off, c + off, a + off)]
    low = {}
    for t in T[0::4] + T[1::4]:
        for k in range(3):
            low[(t[k], t[(k + 1) % 3])] = 1
    for (p, q) in list(low):
        if (q, p) not in low:
            T += [(q, p, p + off), (q, p + off, q + off)]
    V, T = np.asarray(V), np.asarray(T)
    if signed_volume(V, T) < 0:
        T = T[:, ::-1]
    return V, T


def signed_volume(V, T):
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def is_closed(V, T):
    e = {}
    for t in T:
        for k in range(3):
            key = (int(t[k]), int(t[(k + 1) % 3]))
            e[key] = e.get(key, 0) + 1
    return all(v == 1 for v in e.values()) and all((q, p) in e for (p, q) in e)


def disc_solid(R, z0, z1, n=48):
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.column_stack([R * np.cos(ang), R * np.sin(ang)])
    V = np.vstack([np.column_stack([ring, np.full(n, z0)]), np.column_stack([ring, np.full(n, z1)]), [[0, 0, z0]], [[0, 0, z1]]])
    T = []
    for k in range(n):
        k2 = (k + 1) % n
        T += [(k, k2, 2 * n), (n + k2, n + k, 2 * n + 1), (k, n + k, k2), (k2, n + k, n + k2)]
    V, T = np.asarray(V), np.asarray(T)
    if signed_volume(V, T) < 0:
        T = T[:, ::-1]
    return V, T


def r_cone(z, p):
    return p["R_bot"] + (p["R_top"] - p["R_bot"]) * z / p["H"]

def vane_sheet(v, p):
    """Срединная поверхность лопасти v: корень на конусе, внешний край по эллипсоиду, скручивание и волна."""
    H, N = p["H"], p["N"]
    t = np.linspace(0.015, 0.985, int(p["Nz"]))
    s = np.linspace(0, 1, int(p["Ns"]))
    z = H * t
    rr = r_cone(z, p)
    renv = rr + (p["R_bulge"] - rr) * np.sin(np.pi * t) ** p["bulge_pow"]
    b = math.radians(p["sweep_deg"])
    L = np.maximum(-rr * math.cos(b) + np.sqrt(np.maximum(renv ** 2 - (rr * math.sin(b)) ** 2, 0)), 1.0)
    phi = 2 * np.pi * v / N - p["macro_twist"] * t
    er = np.column_stack([np.cos(phi), np.sin(phi), np.zeros_like(phi)])
    et = np.column_stack([-np.sin(phi), np.cos(phi), np.zeros_like(phi)])
    dirh = math.cos(b) * er - math.sin(b) * et
    nh = np.column_stack([-dirh[:, 1], dirh[:, 0], np.zeros_like(phi)])
    root = np.column_stack([rr * np.cos(phi), rr * np.sin(phi), z])
    ell = L[:, None] * s[None, :]
    lmax = L.max()
    k0 = math.radians(p["twist_deg_per_cm"]) / 10.0
    theta = k0 * (ell + p["twist_accel"] * (ell - ell ** 2 / (2 * lmax)))
    zc = H / 2
    u = (z - zc)[:, None]
    S = np.zeros((len(t), len(s), 3))
    S[:, :, :2] = root[:, None, :2] + ell[:, :, None] * dirh[:, None, :2] - (u * np.sin(theta))[:, :, None] * nh[:, None, :2]
    S[:, :, 2] = zc + u * np.cos(theta)
    if p["wave_A"] > 0:
        dI, dJ = np.gradient(S, axis=0), np.gradient(S, axis=1)
        Nn = np.cross(dI, dJ)
        Nn /= np.maximum(np.linalg.norm(Nn, axis=2, keepdims=True), 1e-12)
        c = math.radians(p["crest_deg"])
        ph = 2 * np.pi * (-ell * math.sin(c) + u * math.cos(c)) / p["wave_lambda"] + math.radians(p["wave_phase_deg"]) * v
        w = p["wave_A"] * np.sin(ph) * ss(ell / p["wave_ramp"])
        S = S + Nn * w[:, :, None]
    return S


def wall_panel(z0, z1, a0, a1, p, nz=8, na=6):
    z = np.linspace(z0, z1, nz)
    a = np.linspace(a0, a1, na)
    r = r_cone(z, p)
    S = np.stack([r[:, None] * np.cos(a)[None, :], r[:, None] * np.sin(a)[None, :], np.repeat(z[:, None], na, 1)], axis=2)
    return thick_sheet(S, p["wall_t"])


def door_flap(phi_h, z0, z1, width, p):
    """ИСПРАВЛЕНО: Дверца теперь плавно наклонена по высоте.
    Нижняя точка приоткрыта стандартно, верхняя — задрана сильнее вверх по Z, создавая винтовой трамплин.
    """
    al = math.radians(p["door_angle_deg"])
    er = np.array([math.cos(phi_h), math.sin(phi_h), 0.0])
    et = np.array([-math.sin(phi_h), math.cos(phi_h), 0.0])

    # Вектор отгибания створки внутрь
    v_open = width * (math.cos(al) * (-et) + math.sin(al) * (-er))

    # Корни петель на стенке
    H0 = r_cone(z0, p) * er + np.array([0, 0, z0]) - er * p["wall_t"] * 0.4
    H1 = r_cone(z1, p) * er + np.array([0, 0, z1]) - er * p["wall_t"] * 0.4

    # Свободный край (приоткрытый). У нижней кромки подъем 0, у верхней - максимальный door_lift
    p_low_open = H0 + v_open
    p_high_open = H1 + v_open + np.array([0, 0, p["door_lift"]])

    # Дискретизация плоскости створки в матрицу (2, 2, 3) для thick_sheet
    S = np.zeros((2, 2, 3))
    S[0, 0] = H0
    S[0, 1] = p_low_open
    S[1, 0] = H1
    S[1, 1] = p_high_open

    return thick_sheet(S, p["door_t"])


def build(p):
    solids, names = [], []
    N, H = int(p["N"]), p["H"]
    pitch = 2 * np.pi / N
    eps = 0.01
    for v in range(N):
        solids.append(thick_sheet(vane_sheet(v, p), p["vane_t"]))
        names.append(f"vane{v}")
    solids.append(disc_solid(p["R_bot"] + p["wall_t"] / 2, 0.0, p["floor_t"]))
    names.append("floor")
    z0, zd = p["floor_t"], p["floor_t"] + p["door_h_frac"] * H
    for k in range(N):
        a0, a1 = k * pitch - eps, (k + 1) * pitch + eps
        if k % int(p["door_every"]) != 0:
            solids.append(wall_panel(0.0, H, a0, a1, p, nz=20))
            names.append(f"wall{k}")
            continue
        ac = (k + 0.5) * pitch
        half = 0.5 * p["door_fill"] * pitch
        solids.append(wall_panel(0.0, z0 + eps, a0, a1, p, nz=3))
        names.append(f"wallb{k}")
        solids.append(wall_panel(zd, H, a0, a1, p, nz=18))
        names.append(f"wallt{k}")
        solids.append(wall_panel(z0, zd, a0, ac - half, p, nz=4, na=3))
        names.append(f"pillarL{k}")
        solids.append(wall_panel(z0, zd, ac + half, a1, p, nz=4, na=3))
        names.append(f"pillarR{k}")
        wd = 2 * r_cone(z0, p) * math.sin(half) * 1.0
        solids.append(door_flap(ac + half, z0, zd, wd, p))
        names.append(f"door{k}")
    return solids, names


def write_stl(path, solids, scale):
    tris = []
    for V, T in solids:
        tris.append((V * scale)[T])
    tri = np.concatenate(tris).astype("<f4")
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-20)
    rec = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, tri
    with open(path, "wb") as f:
        f.write(b"cyclone vanes doors".ljust(80, b" "))
        f.write(np.uint32(len(tri)).tobytes())
        rec.tofile(f)
    return len(tri)


if __name__ == "__main__":
    print("Старт генерации 24-лопастной модели...")
    mesh_solids, mesh_names = build(P)
    out_path = "cyclone_v16_final.stl"
    tri_count = write_stl(out_path, mesh_solids, P["units"])
    print(f"Успешно сохранено! Файл: {out_path}, Всего треугольников: {tri_count}")
