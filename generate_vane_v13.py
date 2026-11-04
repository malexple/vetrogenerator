import math
import numpy as np

def write_stl(filename, facets):
    """Записывает массив треугольников в текстовый формат STL."""
    with open(filename, 'w') as f:
        f.write("solid cyclone_doors_v13\n")
        for facet in facets:
            p1, p2, p3 = facet[0], facet[1], facet[2]

            # Расчет нормали
            v1 = p2 - p1
            v2 = p3 - p1
            n = np.cross(v1, v2)
            norm = np.linalg.norm(n)
            if norm > 1e-7:
                n = n / norm
            else:
                n = np.array([0.0, 0.0, 1.0])

            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {p1[0]:.6e} {p1[1]:.6e} {p1[2]:.6e}\n")
            f.write(f"      vertex {p2[0]:.6e} {p2[1]:.6e} {p2[2]:.6e}\n")
            f.write(f"      vertex {p3[0]:.6e} {p3[1]:.6e} {p3[2]:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid cyclone_doors_v13\n")

def generate_vortex_geometry():
    # --- ГЕОМЕТРИЧЕСКИЕ ПАРАМЕТРЫ ---
    Height = 300.0           # Высота (300 мм)
    R_base_bottom = 90.0     # Радиус снизу (мм)
    R_base_top = 30.0        # Радиус сверху (мм)
    R_max_bulge = 160.0      # Раздутие экватора (мм)

    N_vanes = 24             # 24 лопасти
    Vane_thickness = 1.8     # Толщина лопасти (мм)
    N_doors = 6              # 6 приоткрытых воздушных дверец внутри

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

    # === ЭТАП 1: ГЕНЕРАЦИЯ ЛЕПЕСТКОВ ===
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

            cone_outer[i, v] = np.array([r_cone * math.cos(phi_center), r_cone * math.sin(phi_center), z])

            # Внутренний пустой канал конуса (10% отверстие снизу)
            r_inner = (R_base_bottom * 0.10) * (1.0 - 0.8 * t_z)
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

        # Сборка триангуляции лопастей
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

    # === ЭТАП 2: СБОРКА СТЕНКА КОНУСА И ОКРУЖНОСТЕЙ ===
    for i in range(N_z - 1):
        for v in range(N_vanes):
            v_next = (v + 1) % N_vanes
            # Внешняя стенка конуса
            facets.append([cone_outer[i, v], cone_outer[i+1, v_next], cone_outer[i+1, v]])
            facets.append([cone_outer[i, v], cone_outer[i, v_next], cone_outer[i+1, v_next]])

            # Строим внутреннюю пограничную стенку (трубу) только там, где нет дверец
            if v % (N_vanes // N_doors) != 0:
                facets.append([cone_inner[i, v], cone_inner[i+1, v], cone_inner[i+1, v_next]])
                facets.append([cone_inner[i, v], cone_inner[i+1, v_next], cone_inner[i, v_next]])

    # Нижний кольцевой торец
    for v in range(N_vanes):
        v_next = (v + 1) % N_vanes
        facets.append([cone_inner[0, v], cone_outer[0, v_next], cone_outer[0, v]])
        facets.append([cone_inner[0, v], cone_inner[0, v_next], outer_pt := cone_outer[0, v_next]])

    # === ЭТАП 3: СОЗДАНИЕ ПРИОТКРЫТЫХ И НАКЛОНЕННЫХ ДВЕРЕЦ ===
    door_step = N_vanes // N_doors
    for b in range(N_doors):
        v_idx = b * door_step
        v_next = (v_idx + 1) % N_vanes

        for i in range(N_z - 1):
            t_z = i / (N_z - 1)
            # Точки прорези на внутренней трубе
            p_edge0 = cone_inner[i, v_idx]
            p_edge1 = cone_inner[i+1, v_idx]

            # Математика «отгибания» дверцы внутрь канала
            phi_door = (2 * math.pi / N_vanes) * v_idx - (t_z * Macro_twist)
            # Вектор закрутки внутрь + наклон вверх (+15 градусов к шагу оси Z)
            angle_open = 0.5  # угол приоткрытия створок в радианах

            r_inner_now = (R_base_bottom * 0.10) * (1.0 - 0.8 * t_z)

            # Вычисляем смещенную (приоткрытую) кромку дверцы
            x_open0 = (r_inner_now * 0.7) * math.cos(phi_door + angle_open)
            y_open0 = (r_inner_now * 0.7) * math.sin(phi_door + angle_open)
            # Трамплин: приподнимаем свободный край приоткрытой дверцы на 12 мм вверх для закрутки
            z_open0 = (i * (Height / (N_z - 1))) + 12.0
            p_open0 = np.array([x_open0, y_open0, z_open0])

            t_z_next = (i+1) / (N_z - 1)
            r_inner_next = (R_base_bottom * 0.10) * (1.0 - 0.8 * t_z_next)
            x_open1 = (r_inner_next * 0.7) * math.cos(phi_door + angle_open)
            y_open1 = (r_inner_next * 0.7) * math.sin(phi_door + angle_open)
            z_open1 = ((i+1) * (Height / (N_z - 1))) + 12.0
            p_open1 = np.array([x_open1, y_open1, z_open1])

            # Генерируем геометрию приоткрытой пластины-нагнетателя
            facets.append([p_edge0, p_open1, p_edge1])
            facets.append([p_edge0, p_open0, p_open1])

    return facets

if __name__ == "__main__":
    print("Генерация циклонного сепаратора со створками-нагнетателями...")
    mesh_facets = generate_vortex_geometry()
    output_file = "cyclone_sphere_v13.stl"
    print(f"Сохранение в {output_file}...")
    write_stl(output_file, mesh_facets)
    print("Успешно завершено! Файл cyclone_sphere_v13.stl записан без ошибок.")
