import math
import numpy as np

def write_stl(filename, facets):
    """Записывает массив треугольников в текстовый формат STL."""
    with open(filename, 'w') as f:
        f.write("solid cyclone_sphere_v3\n")
        for facet in facets:
            # ИСПРАВЛЕНО: Правильная распаковка трех точек треугольника
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
        f.write("endsolid cyclone_sphere_v3\n")

def generate_vortex_geometry():
    # --- ГЕОМЕТРИЧЕСКИЕ ПАРАМЕТРЫ ДЛЯ ВЫСОТЫ 30 СМ ---
    Height = 300.0       # Высота конструкции (300 мм)
    R_max = 120.0        # Максимальный радиус «шара» в центре (мм)
    R_base = 60.0        # Радиус у основания и вершины (мм)
    N_vanes = 12         # 12 лепестков
    Vane_thickness = 2.0 # Толщина лепестка (мм)

    # --- ПАРАМЕТРЫ ЗАКРУТКИ И НАПРАВЛЯЮЩИХ ВОЛН ---
    Macro_twist = 2.5    # Общая макро-закрутка (в радианах на всю длину)
    Twist_rate = 0.015   # Скорость скручивания поверхности лепестка (рад/мм)

    # Параметры направляющих волн
    Wave_amplitude = 6.0 # Глубина бороздок (мм)
    Wave_frequency = 6.0 # Количество волн по всей высоте
    Wave_tilt = 2.0      # Наклон волны для направления потока вниз

    facets = []

    # Дискретизация сетки
    N_z = 80
    N_w = 25

    for v in range(N_vanes):
        base_phi = (2 * math.pi / N_vanes) * v

        vane_points_low = np.zeros((N_z, N_w, 3))
        vane_points_high = np.zeros((N_z, N_w, 3))

        for i in range(N_z):
            t_z = i / (N_z - 1)
            z = t_z * Height

            # Сферический профиль бочки
            r_sphere = R_base + (R_max - R_base) * math.sin(math.pi * t_z)

            # Основная макро-спираль
            phi_center = base_phi - (t_z * Macro_twist)

            x_c = r_sphere * math.cos(phi_center)
            y_c = r_sphere * math.sin(phi_center)

            # Базовые векторы ориентации
            radial_dir = np.array([math.cos(phi_center), math.sin(phi_center), 0.0])
            tangent_dir = np.array([-math.sin(phi_center), math.cos(phi_center), 0.0])

            for j in range(N_w):
                t_w = j / (N_w - 1)

                # Ширина лепестка адаптирована под форму шара
                max_width = 75.0 * (0.4 + 0.6 * math.sin(math.pi * t_z))
                w_dist = max_width * math.sin(math.pi * t_w)

                # Скорость скручивания ленты
                local_twist_angle = z * Twist_rate

                # Направляющая волна
                wave_phase = Wave_frequency * math.pi * t_z + (t_w * Wave_tilt * math.pi)
                wave_offset = Wave_amplitude * math.sin(wave_phase)

                total_local_angle = local_twist_angle

                # Смещение по ширине и за счет волны
                offset_vec = w_dist * (math.cos(total_local_angle) * tangent_dir + math.sin(total_local_angle) * radial_dir)
                wave_vec = wave_offset * (math.cos(total_local_angle + math.pi/2) * tangent_dir + math.sin(total_local_angle + math.pi/2) * radial_dir)

                thickness_vec = np.array([0.0, 0.0, Vane_thickness])

                vane_points_low[i, j] = np.array([x_c, y_c, z]) + offset_vec + wave_vec
                vane_points_high[i, j] = vane_points_low[i, j] + thickness_vec

        # Сборка треугольников STL
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
    print("Генерация сферического 12-лепесткового завихрителя (30 см)...")
    mesh_facets = generate_vortex_geometry()
    output_file = "cyclone_sphere_v3.stl"
    print(f"Сохранение в {output_file}...")
    write_stl(output_file, mesh_facets)
    print("Готово! Ошибок нет. Откройте файл cyclone_sphere_v3.stl.")
