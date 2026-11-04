import math
import numpy as np

def write_stl(filename, facets):
    """Записывает массив треугольников в текстовый формат STL."""
    with open(filename, 'w') as f:
        f.write("solid cyclone_baffles_v12\n")
        for facet in facets:
            p1 = facet[0]
            p2 = facet[1]
            p3 = facet[2]

            # Расчет нормали
            v1 = p2 - p1
            v2 = p3 - p1
            n = np.cross(v1, v2)
            norm = np.linalg.norm(n)
            if norm > 1e-7:
                n = n / norm
            else:
                n = np.array([0.0, 0.0, 1.0])

            # ИСПРАВЛЕНО ОКОНЧАТЕЛЬНО: Извлечение элементов по индексам, [1], [2]
            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {p1[0]:.6e} {p1[1]:.6e} {p1[2]:.6e}\n")
            f.write(f"      vertex {p2[0]:.6e} {p2[1]:.6e} {p2[2]:.6e}\n")
            f.write(f"      vertex {p3[0]:.6e} {p3[1]:.6e} {p3[2]:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid cyclone_baffles_v12\n")

def generate_vortex_geometry():
    # --- ГЕОМЕТРИЧЕСКИЕ ПАРАМЕТРЫ ---
    Height = 300.0           # Высота конструкции (300 мм)
    R_base_bottom = 90.0     # Большой радиус снизу (мм)
    R_base_top = 30.0        # Маленький радиус сверху (мм)
    R_max_bulge = 160.0      # Раздутие "бочки" на экваторе (мм)

    N_vanes = 24             # 24 лопасти
    Vane_thickness = 1.8     # Толщина лопасти (мм)
    N_baffles = 6            # Количество внутренних перегородок против выдувания

    # --- ПАРАМЕТРЫ ЗАКРУТКИ И ГЛУБОКИХ ВОЛН ---
    Macro_twist = 2.4
    Twist_rate = 0.007

    Wave_amplitude_radial = 12.0
    Wave_amplitude_axial = -10.0
    Wave_frequency = 5.0
    Wave_tilt = 2.0

    facets = []

    N_z = 120
    N_w = 35

    cone_outer = np.zeros((N_z, N_vanes, 3))
    cone_inner = np.zeros((N_z, N_vanes, 3))

    # === ЭТАП 1: ГЕНЕРАЦИЯ ЛЕПЕСТКОВ СТРОГО ПО КРУГУ ===
    for v in range(N_vanes):
        base_phi = (2 * math.pi / N_vanes) * v

        vane_points_low = np.zeros((N_z, N_w, 3))
        vane_points_high = np.zeros((N_z, N_w, 3))

        for i in range(N_z):
            t_z = i / (N_z - 1)
            z = t_z * Height

            r_cone = R_base_bottom - t_z * (R_base_bottom - R_base_top)
            r_sphere = r_cone + (R_max_bulge - r_cone) * math.sin(math.pi * t_z)

            phi_center = base_phi - (t_z * Macro_twist)

            x_c = r_sphere * math.cos(phi_center)
            y_c = r_sphere * math.sin(phi_center)

            # Сохраняем опорные точки для конуса
            x_cone_surface = r_cone * math.cos(phi_center)
            y_cone_surface = r_cone * math.sin(phi_center)
            cone_outer[i, v] = np.array([x_cone_surface, y_cone_surface, z])

            r_inner = (R_base_bottom * 0.10) * (1.0 - t_z)
            cone_inner[i, v] = np.array([r_inner * math.cos(phi_center), r_inner * math.sin(phi_center), z])

            radial_dir = np.array([math.cos(phi_center), math.sin(phi_center), 0.0])
            tangent_dir = np.array([-math.sin(phi_center), math.cos(phi_center), 0.0])

            for j in range(N_w):
                t_w = j / (N_w - 1)

                equator_narrowing = 1.0 - 0.45 * math.sin(math.pi * t_z)
                max_width = 95.0 * equator_narrowing * (r_sphere / R_max_bulge)
                w_dist = max_width * math.sin(math.pi * t_w)

                local_twist_angle = z * Twist_rate

                wave_phase = Wave_frequency * math.pi * t_z + (t_w * Wave_tilt * math.pi)
                wave_offset_r = Wave_amplitude_radial * math.sin(wave_phase)
                wave_offset_z = Wave_amplitude_axial * math.cos(wave_phase)

                offset_vec = w_dist * (math.cos(local_twist_angle) * tangent_dir + math.sin(local_twist_angle) * radial_dir)
                wave_normal_dir = (math.cos(local_twist_angle + math.pi/2) * tangent_dir +
                                   math.sin(local_twist_angle + math.pi/2) * radial_dir)

                sculpt_vec = (wave_offset_r * wave_normal_dir) + np.array([0.0, 0.0, wave_offset_z])
                thickness_vec = Vane_thickness * wave_normal_dir

                vane_points_low[i, j] = np.array([x_c, y_c, z]) + offset_vec + sculpt_vec
                vane_points_high[i, j] = vane_points_low[i, j] + thickness_vec

        # Триангуляция лепестков
        for i in range(N_z - 1):
            for j in range(N_w - 1):
                facets.append([vane_points_low[i, j], vane_points_low[i+1, j], vane_points_low[i+1, j+1]])
                facets.append([vane_points_low[i, j], vane_points_low[i+1, j+1], vane_points_low[i, j+1]])

                facets.append([vane_points_high[i, j], vane_points_high[i+1, j], vane_points_high[i+1, j+1]])
                facets.append([vane_points_high[i, j], vane_points_high[i+1, j+1], vane_points_high[i, j+1]])

            facets.append([vane_points_low[i, 0], vane_points_high[i+1, 0], vane_points_low[i+1, 0]])
            facets.append([vane_points_low[i, 0], vane_points_high[i, 0], vane_points_high[i+1, 0]])
            facets.append([vane_points_low[i, N_w-1], vane_points_low[i+1, N_w-1], vane_points_high[i+1, N_w-1]])
            facets.append([vane_points_low[i, N_w-1], vane_points_high[i+1, N_w-1], vane_points_high[i, N_w-1]])

    # === ЭТАП 2: ПОСТРОЕНИЕ СПЛОШНОГО ЦЕНТРАЛЬНОГО КОНУСА ===
    for i in range(N_z - 1):
        for v in range(N_vanes):
            v_next = (v + 1) % N_vanes

            # Наружная обшивка
            facets.append([cone_outer[i, v], cone_outer[i+1, v_next], cone_outer[i+1, v]])
            facets.append([cone_outer[i, v], cone_outer[i, v_next], cone_outer[i+1, v_next]])

            # Внутренняя обшивка (полая труба)
            facets.append([cone_inner[i, v], cone_inner[i+1, v], cone_inner[i+1, v_next]])
            facets.append([cone_inner[i, v], cone_inner[i+1, v_next], cone_inner[i, v_next]])

    # Нижний фланец конуса
    for v in range(N_vanes):
        v_next = (v + 1) % N_vanes
        facets.append([cone_inner[0, v], cone_outer[0, v_next], cone_outer[0, v]])
        facets.append([cone_inner[0, v], cone_inner[0, v_next], cone_outer[0, v_next]])

    # === ЭТАП 3: ДОБАВЛЕНИЕ ВНУТРЕННИХ ПЕРЕГОРОДОК (АНТИ-ВЫДУВАНИЕ) ===
    step_baffle = N_vanes // N_baffles  # Интервал установки (каждые 4 лопасти при N=24)

    for b in range(N_baffles):
        v_idx = b * step_baffle

        for i in range(N_z - 1):
            p_out0 = cone_outer[i, v_idx]
            p_out1 = cone_outer[i+1, v_idx]
            p_in0 = cone_inner[i, v_idx]
            p_in1 = cone_inner[i+1, v_idx]

            facets.append([p_in0, p_out1, p_out0])
            facets.append([p_in0, p_in1, p_out1])

    return facets

if __name__ == "__main__":
    print("Генерация 24-реберного завихрителя с внутренними противовыдувными перегородками...")
    mesh_facets = generate_vortex_geometry()
    output_file = "cyclone_sphere_v12.stl"
    print(f"Сохранение в {output_file}...")
    write_stl(output_file, mesh_facets)
    print("Успешно выполнено! Внутренние лабиринтные перегородки интегрированы в STL.")
