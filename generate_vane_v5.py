import math
import numpy as np

def write_stl(filename, facets):
    """Записывает массив треугольников в текстовый формат STL."""
    with open(filename, 'w') as f:
        f.write("solid cyclone_ultra_wide_v5\n")
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
        f.write("endsolid cyclone_ultra_wide_v5\n")

def generate_vortex_geometry():
    # --- ГЕОМЕТРИЧЕСКИЕ ПАРАМЕТРЫ (ВЫСОТА 30 СМ) ---
    Height = 300.0       # Высота конструкции (300 мм)
    R_max = 140.0        # Максимальный радиус сферы в центре (мм)
    R_base = 50.0        # Радиус у основания и вершины (мм)
    N_vanes = 12         # 12 статичных лепестков
    Vane_thickness = 3.0 # Толщина (мм) — увеличили до 3 мм для жесткости широких лопастей

    # --- ПАРАМЕТРЫ ЗАКРУТКИ И НАПРАВЛЯЮЩИХ ВОЛН ---
    Macro_twist = 2.0    # Шаг закрутки вокруг оси конуса
    Twist_rate = 0.010   # Внутреннее скручивание лепестка

    # Скульптурная волна, направляющая воздух строго вниз
    Wave_amplitude_radial = 16.0  # Радиальная глубина складок (мм)
    Wave_amplitude_axial = -12.0  # Осевой сдвиг (отрицательный, чтобы толкать поток вниз)
    Wave_frequency = 5.0          # Плотность волн по высоте
    Wave_tilt = 2.2               # Крутизна наклона гофра

    facets = []

    # Повышаем плотность сетки для гладких перекрытий огромных лепестков
    N_z = 120
    N_w = 35

    for v in range(N_vanes):
        base_phi = (2 * math.pi / N_vanes) * v

        vane_points_low = np.zeros((N_z, N_w, 3))
        vane_points_high = np.zeros((N_z, N_w, 3))

        for i in range(N_z):
            t_z = i / (N_z - 1)
            z = t_z * Height

            # Профиль шара
            r_sphere = R_base + (R_max - R_base) * math.sin(math.pi * t_z)

            # Макро-спираль
            phi_center = base_phi - (t_z * Macro_twist)

            x_c = r_sphere * math.cos(phi_center)
            y_c = r_sphere * math.sin(phi_center)

            radial_dir = np.array([math.cos(phi_center), math.sin(phi_center), 0.0])
            tangent_dir = np.array([-math.sin(phi_center), math.cos(phi_center), 0.0])

            for j in range(N_w):
                t_w = j / (N_w - 1)

                # ИЗМЕНЕНО: Ширина лепестка увеличена в 3 раза (макс. 255 мм в центре)
                max_width = 255.0 * (0.3 + 0.7 * math.sin(math.pi * t_z))
                w_dist = max_width * math.sin(math.pi * t_w)

                local_twist_angle = z * Twist_rate

                # Математика волны "сброса" потока вниз
                wave_phase = Wave_frequency * math.pi * t_z + (t_w * Wave_tilt * math.pi)

                wave_offset_r = Wave_amplitude_radial * math.sin(wave_phase)
                wave_offset_z = Wave_amplitude_axial * math.cos(wave_phase)

                total_local_angle = local_twist_angle

                # Основной вектор ширины
                offset_vec = w_dist * (math.cos(total_local_angle) * tangent_dir + math.sin(total_local_angle) * radial_dir)

                # Направление волны (перпендикулярно плоскости лопасти)
                wave_normal_dir = (math.cos(total_local_angle + math.pi/2) * tangent_dir +
                                   math.sin(total_local_angle + math.pi/2) * radial_dir)

                # Суммируем трехмерную деформацию (карманы + принудительное скольжение вниз)
                sculpt_vec = (wave_offset_r * wave_normal_dir) + np.array([0.0, 0.0, wave_offset_z])
                thickness_vec = Vane_thickness * wave_normal_dir

                vane_points_low[i, j] = np.array([x_c, y_c, z]) + offset_vec + sculpt_vec
                vane_points_high[i, j] = vane_points_low[i, j] + thickness_vec

        # Сборка триангуляции STL
        for i in range(N_z - 1):
            for j in range(N_w - 1):
                p00 = vane_points_low[i, j]
                p10 = vane_points_low[i+1, j]
                p01 = vane_points_low[i, j+1]
                p11 = vane_points_low[i+1, j+1]
                facets.append([p00, p10, p11])
                facets.append([p00, p11, p01])

                p00_h = vane_points_high[i, j]
                p10_h = vane_points_high[i+1, j]
                p01_h = vane_points_high[i, j+1]
                p11_h = vane_points_high[i+1, j+1]
                facets.append([p00_h, p11_h, p10_h])
                facets.append([p00_h, p01_h, p11_h])

            facets.append([vane_points_low[i, 0], vane_points_high[i+1, 0], vane_points_low[i+1, 0]])
            facets.append([vane_points_low[i, 0], vane_points_high[i, 0], vane_points_high[i+1, 0]])
            facets.append([vane_points_low[i, N_w-1], vane_points_low[i+1, N_w-1], vane_points_high[i+1, N_w-1]])
            facets.append([vane_points_low[i, N_w-1], vane_points_high[i+1, N_w-1], vane_points_high[i, N_w-1]])

    return facets

if __name__ == "__main__":
    print("Генерация ультра-широкого сферического завихрителя...")
    mesh_facets = generate_vortex_geometry()
    output_file = "cyclone_sphere_v5.stl"
    print(f"Сохранение в {output_file}...")
    write_stl(output_file, mesh_facets)
    print("Готово! Новая трехмерная модель сохранена.")
