import math
import numpy as np

def write_stl(filename, facets):
    """Записывает массив треугольников в текстовый формат STL."""
    with open(filename, 'w') as f:
        f.write("solid cyclone_vane_v2\n")
        for facet in facets:
            p1, p2, p3 = facet[0], facet[1], facet[2]
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
        f.write("endsolid cyclone_vane_v2\n")

def generate_vortex_geometry():
    # --- ГЕОМЕТРИЧЕСКИЕ ПАРАМЕТРЫ ---
    R_bottom = 50.0      # Радиус конуса снизу (мм)
    R_top = 20.0         # Радиус конуса сверху (мм)
    Height = 80.0        # Высота конуса (мм)
    N_vanes = 12         # Новое количество лепестков: 12 штук
    Vane_thickness = 1.2 # Толщина лепестка (мм)

    # --- ПАРАМЕТРЫ ЗАКРУТКИ И НАПРАВЛЯЮЩИХ ВОЛН ---
    Macro_twist = 1.8    # Угол закрутки вокруг конуса (в радианах)
    Twist_rate = 0.04    # Скорость скручивания поверхности лепестка (рад/мм)

    # Волны, направляющие поток вниз:
    Wave_amplitude = 2.0 # Глубина бороздок (мм)
    Wave_frequency = 5.0 # Частота волн по высоте
    # Коэффициент наклона волны (направляет поток вниз конуса по ходу вращения)
    Wave_tilt = 1.5

    facets = []

    # Дискретизация (увеличена плотность для гладкости волн)
    N_z = 60
    N_w = 20

    for v in range(N_vanes):
        base_phi = (2 * math.pi / N_vanes) * v

        vane_points_low = np.zeros((N_z, N_w, 3))
        vane_points_high = np.zeros((N_z, N_w, 3))

        for i in range(N_z):
            t_z = i / (N_z - 1)
            z = t_z * Height

            # Текущий радиус несущего конуса
            r_cone = R_bottom - t_z * (R_bottom - R_top)

            # Основная спираль (макро-закрутка)
            phi_center = base_phi - (t_z * Macro_twist)

            x_c = r_cone * math.cos(phi_center)
            y_c = r_cone * math.sin(phi_center)

            # Локальный базис для построения профиля лепестка
            radial_dir = np.array([math.cos(phi_center), math.sin(phi_center), 0.0])
            tangent_dir = np.array([-math.sin(phi_center), math.cos(phi_center), 0.0])

            for j in range(N_w):
                t_w = j / (N_w - 1)

                # Ширина лепестка плавно уменьшается к вершине конуса
                max_width = 18.0 * (1.0 - 0.4 * t_z)
                w_dist = max_width * math.sin(math.pi * t_w)

                # Параметризация локального скручивания ленты
                local_twist_angle = z * Twist_rate

                # НАПРАВЛЯЮЩАЯ ВОЛНА: связываем координату высоты t_z и ширины t_w.
                # Знак плюс перед (t_w * Wave_tilt) наклоняет гребни волн так,
                # чтобы скользящий воздух сваливался по ним по направлению к основанию (вниз).
                wave_phase = Wave_frequency * math.pi * t_z + (t_w * Wave_tilt * math.pi)
                wave_offset = Wave_amplitude * math.sin(wave_phase)

                # Результирующий угол поворота сечения лепестка
                total_local_angle = local_twist_angle

                # Расчет нормальных смещений (ошибка осей исправлена)
                offset_vec = w_dist * (math.cos(total_local_angle) * tangent_dir + math.sin(total_local_angle) * radial_dir)

                # Сама волна теперь работает как гофрированная складка (смещение по нормали к лепестку)
                wave_vec = wave_offset * (math.cos(total_local_angle + math.pi/2) * tangent_dir + math.sin(total_local_angle + math.pi/2) * radial_dir)

                # Направление вектора толщины (вдоль оси Z для стабильной печати/генерации)
                thickness_vec = np.array([0.0, 0.0, Vane_thickness])

                # Конечные координаты точек нижней и верхней поверхностей
                vane_points_low[i, j] = np.array([x_c, y_c, z]) + offset_vec + wave_vec
                vane_points_high[i, j] = vane_points_low[i, j] + thickness_vec

        # Генерация полигональной сетки (треугольников)
        for i in range(N_z - 1):
            for j in range(N_w - 1):
                # Нижняя сторона лепестка
                p00 = vane_points_low[i, j]
                p10 = vane_points_low[i+1, j]
                p01 = vane_points_low[i, j+1]
                p11 = vane_points_low[i+1, j+1]
                facets.append([p00, p10, p11])
                facets.append([p00, p11, p01])

                # Верхняя сторона лепестка
                p00_h = vane_points_high[i, j]
                p10_h = vane_points_high[i+1, j]
                p01_h = vane_points_high[i, j+1]
                p11_h = vane_points_high[i+1, j+1]
                facets.append([p00_h, p11_h, p10_h])
                facets.append([p00_h, p01_h, p11_h])

            # Закрываем торцы по бокам лепестков
            facets.append([vane_points_low[i, 0], vane_points_high[i+1, 0], vane_points_low[i+1, 0]])
            facets.append([vane_points_low[i, 0], vane_points_high[i, 0], vane_points_high[i+1, 0]])
            facets.append([vane_points_low[i, N_w-1], vane_points_low[i+1, N_w-1], vane_points_high[i+1, N_w-1]])
            facets.append([vane_points_low[i, N_w-1], vane_points_high[i+1, N_w-1], vane_points_high[i, N_w-1]])

    return facets

if __name__ == "__main__":
    print("Генерация 12-лепесткового завихрителя с направленной волной...")
    mesh_facets = generate_vortex_geometry()
    output_file = "cyclone_vane_v2.stl"
    print(f"Сохранение в {output_file}...")
    write_stl(output_file, mesh_facets)
    print("Успешно завершено! Откройте новую модель в ParaView.")
