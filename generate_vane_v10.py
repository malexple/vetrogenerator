import math
import numpy as np

def write_stl(filename, facets):
    """Записывает массив треугольников в текстовый формат STL."""
    with open(filename, 'w') as f:
        f.write("solid cyclone_24_vanes_v10\n")
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

            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {p1[0]:.6e} {p1[1]:.6e} {p1[2]:.6e}\n")
            f.write(f"      vertex {p2[0]:.6e} {p2[1]:.6e} {p2[2]:.6e}\n")
            f.write(f"      vertex {p3[0]:.6e} {p3[1]:.6e} {p3[2]:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid cyclone_24_vanes_v10\n")

def generate_vortex_geometry():
    # --- ГЕОМЕТРИЧЕСКИЕ ПАРАМЕТРЫ ---
    Height = 300.0           # Высота конструкции (300 мм)
    R_base_bottom = 90.0     # Большой радиус снизу (мм)
    R_base_top = 30.0        # Маленький радиус сверху (мм)
    R_max_bulge = 160.0      # Раздутие "бочки" на экваторе (мм)

    # ИЗМЕНЕНО: Теперь 24 лепестка для сверхплотного вихря
    N_vanes = 24
    Vane_thickness = 2.0     # Чуть уменьшили толщину (с 3 до 2 мм), чтобы 24 ребра не съедали объем каналов

    # --- ПАРАМЕТРЫ ЗАКРУТКИ И НАПРАВЛЯЮЩИХ ВОЛН ---
    Macro_twist = 2.4
    Twist_rate = 0.007

    # Скульптурная волна, гонящая воздух вниз
    Wave_amplitude_radial = 14.0
    Wave_amplitude_axial = -12.0
    Wave_frequency = 5.0
    Wave_tilt = 2.0

    facets = []

    N_z = 120
    N_w = 35

    # Массивы для построения полого центрального конуса
    N_cone_steps = 48        # Увеличили плотность конуса для соответствия 24 ребрам
    cone_outer = np.zeros((N_z, N_cone_steps, 3))
    cone_inner = np.zeros((N_z, N_cone_steps, 3))

    # === ЭТАП 1: ГЕНЕРАЦИЯ 24 ЛЕПЕСТКОВ ===
    for v in range(N_vanes):
        base_phi = (2 * math.pi / N_vanes) * v

        vane_points_low = np.zeros((N_z, N_w, 3))
        vane_points_high = np.zeros((N_z, N_w, 3))

        for i in range(N_z):
            t_z = i / (N_z - 1)
            z = t_z * Height

            # Траектории несущих поверхностей
            r_cone = R_base_bottom - t_z * (R_base_bottom - R_base_top)
            r_sphere = r_cone + (R_max_bulge - r_cone) * math.sin(math.pi * t_z)

            phi_center = base_phi - (t_z * Macro_twist)

            x_c = r_sphere * math.cos(phi_center)
            y_c = r_sphere * math.sin(phi_center)

            radial_dir = np.array([math.cos(phi_center), math.sin(phi_center), 0.0])
            tangent_dir = np.array([-math.sin(phi_center), math.cos(phi_center), 0.0])

            for j in range(N_w):
                t_w = j / (N_w - 1)

                # ИЗМЕНЕНО: Оптимизировали максимальную ширину (со 180 до 120 мм).
                # При 24 ребрах такая ширина сохраняет красивое перекрытие «чешуей», но оставляет каналы открытыми.
                equator_narrowing = 1.0 - 0.45 * math.sin(math.pi * t_z)
                max_width = 120.0 * equator_narrowing * (r_sphere / R_max_bulge)
                w_dist = max_width * math.sin(math.pi * t_w)

                local_twist_angle = z * Twist_rate

                wave_phase = Wave_frequency * math.pi * t_z + (t_w * Wave_tilt * math.pi)
                wave_offset_r = Wave_amplitude_radial * math.sin(wave_phase)
                wave_offset_z = Wave_amplitude_axial * math.cos(wave_phase)

                total_local_angle = local_twist_angle

                offset_vec = w_dist * (math.cos(total_local_angle) * tangent_dir + math.sin(total_local_angle) * radial_dir)
                wave_normal_dir = (math.cos(total_local_angle + math.pi/2) * tangent_dir +
                                   math.sin(total_local_angle + math.pi/2) * radial_dir)

                sculpt_vec = (wave_offset_r * wave_normal_dir) + np.array([0.0, 0.0, wave_offset_z])
                thickness_vec = Vane_thickness * wave_normal_dir

                vane_points_low[i, j] = np.array([x_c, y_c, z]) + offset_vec + sculpt_vec
                vane_points_high[i, j] = vane_points_low[i, j] + thickness_vec

        # Сборка триангуляции лепестков
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

    # === ЭТАП 2: ГЕНЕРАЦИЯ ЦЕНТРАЛЬНОГО ПОЛОГО КОНУСА ===
    for i in range(N_z):
        t_z = i / (N_z - 1)
        z = t_z * Height

        # Наружный радиус конуса по-прежнему идеально стыкуется с корнями 24 лепестков
        r_outer = R_base_bottom - t_z * (R_base_bottom - R_base_top)

        # Внутренний пустой канал (10% отверстие снизу = 9 мм)
        r_inner_start = R_base_bottom * 0.10
        r_inner = r_inner_start * (1.0 - t_z)

        for c in range(N_cone_steps):
            phi = (2 * math.pi / N_cone_steps) * c
            cone_outer[i, c] = np.array([r_outer * math.cos(phi), r_outer * math.sin(phi), z])
            cone_inner[i, c] = np.array([r_inner * math.cos(phi), r_inner * math.sin(phi), z])

    # Построение стенок конического сердечника
    for i in range(N_z - 1):
        for c in range(N_cone_steps):
            c_next = (c + 1) % N_cone_steps

            facets.append([cone_outer[i, c], cone_outer[i+1, c_next], cone_outer[i+1, c]])
            facets.append([cone_outer[i, c], cone_outer[i, c_next], cone_outer[i+1, c_next]])

            facets.append([cone_inner[i, c], cone_inner[i+1, c], cone_inner[i+1, c_next]])
            facets.append([cone_inner[i, c], cone_inner[i+1, c_next], cone_inner[i, c_next]])

    # Нижний глухой торец конуса (кольцевой фланец)
    for c in range(N_cone_steps):
        c_next = (c + 1) % N_cone_steps
        facets.append([cone_inner[0, c], cone_outer[0, c_next], cone_outer[0, c]])
        facets.append([cone_inner[0, c], cone_inner[0, c_next], cone_outer[0, c_next]])

    return facets

if __name__ == "__main__":
    print("Генерация 24-реберного завихрителя с интегрированным конусом...")
    mesh_facets = generate_vortex_geometry()
    output_file = "cyclone_sphere_v10.stl"
    print(f"Сохранение в {output_file}...")
    write_stl(output_file, mesh_facets)
    print("Успешно выполнено! Новая сверхплотная модель cyclone_sphere_v10.stl готова.")
