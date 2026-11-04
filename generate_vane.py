import math
import numpy as np

def write_stl(filename, facets):
    """Записывает массив треугольников в текстовый формат STL."""
    with open(filename, 'w') as f:
        f.write("solid cyclone_vane\n")
        for facet in facets:
            # Расчет нормали к треугольнику (базовый векторный метод)
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
        f.write("endsolid cyclone_vane\n")

def generate_vortex_geometry():
    # --- ГЕОМЕТРИЧЕСКИЕ ПАРАМЕТРЫ (можно менять для оптимизации) ---
    R_bottom = 50.0      # Радиус конуса снизу (мм)
    R_top = 20.0         # Радиус конуса сверху (мм)
    Height = 80.0        # Высота конуса (мм)
    N_vanes = 6          # Количество лепестков-полумесяцев
    Vane_thickness = 1.5 # Толщина лепестка (мм)

    # --- ПАРАМЕТРЫ ЗАКРУТКИ ---
    Macro_twist = 1.5    # Сила закрутки вокруг конуса (в радианах на всю высоту)
    # Главный параметр: Скорость скручивания поверхности вдоль лепестка (радианы на мм)
    Twist_rate = 0.05
    Wave_amplitude = 2.5 # Амплитуда S-образной волны (мм)
    Wave_frequency = 4.0 # Частота волн вдоль лепестка

    facets = []

    # Дискретизация
    N_z = 40  # Точек по высоте
    N_w = 15  # Точек по ширине лепестка

    for v in range(N_vanes):
        # Стартовый угол для каждого лепестка на окружности
        base_phi = (2 * math.pi / N_vanes) * v

        # Создаем сетку точек для одного лепестка
        vane_points_low = np.zeros((N_z, N_w, 3))
        vane_points_high = np.zeros((N_z, N_w, 3))

        for i in range(N_z):
            t_z = i / (N_z - 1)
            z = t_z * Height

            # Радиус конуса на текущей высоте
            r_cone = R_bottom - t_z * (R_bottom - R_top)

            # 1. Макро-закрутка по часовой стрелке вокруг оси Z
            phi_center = base_phi - (t_z * Macro_twist)

            # Координаты центральной линии лепестка на конусе
            x_c = r_cone * math.cos(phi_center)
            y_c = r_cone * math.sin(phi_center)

            # Векторы ориентации лепестка
            radial_dir = np.array([math.cos(phi_center), math.sin(phi_center), 0])
            tangent_dir = np.array([-math.sin(phi_center), math.cos(phi_center), 0])

            for j in range(N_w):
                t_w = j / (N_w - 1)

                # Форма полумесяца: ширина максимальна внизу и сужается кверху
                max_width = 25.0 * (1.0 - 0.5 * t_z)
                # Профиль полумесяца (параболическое распределение ширины)
                w_dist = max_width * math.sin(math.pi * t_w)

                # 2. Локальное скручивание ленты (Twist_rate) + S-образная волна
                local_twist_angle = z * Twist_rate
                wave_offset = Wave_amplitude * math.sin(Wave_frequency * math.pi * (t_z + t_w))

                # Итоговый угол поворота сечения лепестка
                total_local_angle = local_twist_angle + (wave_offset / 10.0)

                # Сдвиг точки лепестка относительно конуса
                offset_x = w_dist * (math.cos(total_local_angle) * tangent_dir[0] + math.sin(total_local_angle) * radial_dir[0])
                offset_y = w_dist * (math.cos(total_local_angle) * tangent_dir[1] + math.sin(total_local_angle) * radial_dir[1])
                offset_z = wave_offset * 0.5 # Волна дает вертикальное смещение

                # Нижняя и верхняя поверхности лепестка (для придания толщины)
                vane_points_low[i, j] = np.array([x_c + offset_x, y_c + offset_y, z + offset_z])
                vane_points_high[i, j] = vane_points_low[i, j] + np.array([0, 0, Vane_thickness])

        # Строим треугольники (фасеты) по созданной сетке точек
        for i in range(N_z - 1):
            for j in range(N_w - 1):
                # Нижняя грань лепестка
                p00 = vane_points_low[i, j]
                p10 = vane_points_low[i+1, j]
                p01 = vane_points_low[i, j+1]
                p11 = vane_points_low[i+1, j+1]
                facets.append([p00, p10, p11])
                facets.append([p00, p11, p01])

                # Верхняя грань лепестка
                p00_h = vane_points_high[i, j]
                p10_h = vane_points_high[i+1, j]
                p01_h = vane_points_high[i, j+1]
                p11_h = vane_points_high[i+1, j+1]
                facets.append([p00_h, p11_h, p10_h])
                facets.append([p00_h, p01_h, p11_h])

            # Боковые заглушки торцов лепестков (по ширине)
            facets.append([vane_points_low[i, 0], vane_points_high[i+1, 0], vane_points_low[i+1, 0]])
            facets.append([vane_points_low[i, 0], vane_points_high[i, 0], vane_points_high[i+1, 0]])
            facets.append([vane_points_low[i, N_w-1], vane_points_low[i+1, N_w-1], vane_points_high[i+1, N_w-1]])
            facets.append([vane_points_low[i, N_w-1], vane_points_high[i+1, N_w-1], vane_points_high[i, N_w-1]])

    return facets

if __name__ == "__main__":
    print("Генерация трехмерной геометрии лепестков...")
    mesh_facets = generate_vortex_geometry()
    output_file = "cyclone_vane.stl"
    print(f"Сохранение модели в файл {output_file}...")
    write_stl(output_file, mesh_facets)
    print("Готово! Вы можете открыть файл в ParaView или любом 3D-просмотрщике.")
