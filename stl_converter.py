import os
import struct
import sys

def convert_ascii_to_binary_stl(input_path, output_path):
    """
    Конвертирует один ASCII STL файл в бинарный STL формат.
    """
    try:
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Проверяем структуру ASCII STL
        facets = []
        current_facet = None

        for line in lines:
            line = line.strip().lower()
            if line.startswith('facet normal'):
                parts = line.split()
                # Нормаль: (nx, ny, nz)
                normal = [float(parts[2]), float(parts[3]), float(parts[4])]
                current_facet = {'normal': normal, 'vertices': []}
            elif line.startswith('vertex'):
                parts = line.split()
                # Вершина: (x, y, z)
                vertex = [float(parts[1]), float(parts[2]), float(parts[3])]
                if current_facet is not None:
                    current_facet['vertices'].append(vertex)
            elif line.startswith('endfacet'):
                if current_facet and len(current_facet['vertices']) == 3:
                    facets.append(current_facet)
                current_facet = None

        num_triangles = len(facets)
        if num_triangles == 0:
            print(f" Скип: файл {os.path.basename(input_path)} пустой или не является ASCII STL.")
            return False

        # Запись в бинарный формат
        with open(output_path, 'wb') as f:
            # 1. Заголовок (80 байт)
            header = b'Binary STL converted via Python script'.ljust(80, b'\x00')
            f.write(header)

            # 2. Количество треугольников (4 байта, uint32)
            f.write(struct.pack('<I', num_triangles))

            # 3. Данные треугольников
            for facet in facets:
                # Нормаль (3 float)
                f.write(struct.pack('<fff', *facet['normal']))
                # 3 Вершины (каждая по 3 float)
                for vertex in facet['vertices']:
                    f.write(struct.pack('<fff', *vertex))
                # Атрибут (2 байта, обычно 0)
                f.write(struct.pack('<H', 0))

        return True
    except Exception as e:
        print(f" Ошибка при обработке {os.path.basename(input_path)}: {e}")
        return False

def batch_convert_stl_in_folder(folder_path):
    """
    Сканирует папку и конвертирует все текстовые STL файлы.
    """
    if not os.path.exists(folder_path):
        print(" Указанная папка не существует!")
        return

    print(f"Начало сканирования папки: {folder_path}\n" + "-"*50)

    converted_count = 0
    skipped_count = 0

    for filename in os.listdir(folder_path):
        # Ищем только файлы с расширением .stl
        if filename.lower().endswith('.stl'):
            # Проверяем, не является ли файл уже результатом конвертации (заканчивается на b.stl)
            name_part, ext = os.path.splitext(filename)
            if name_part.endswith('b'):
                continue

            input_file = os.path.join(folder_path, filename)

            # Быстрая проверка: бинарный файл или текстовый
            # Текстовый STL всегда начинается со слова "solid"
            is_ascii = False
            try:
                with open(input_file, 'rb') as test_f:
                    start_bytes = test_f.read(5)
                    if start_bytes.lower() == b'solid':
                        is_ascii = True
            except IOError:
                continue

            if not is_ascii:
                print(f" Пропуск: {filename} уже является бинарным.")
                skipped_count += 1
                continue

            # Формируем новое имя с буквой 'b' на конце
            new_filename = f"{name_part}b{ext}"
            output_file = os.path.join(folder_path, new_filename)

            print(f"Конвертация: {filename} -> {new_filename}...")
            if convert_ascii_to_binary_stl(input_file, output_file):
                converted_count += 1

    print("-"*50)
    print(f"Готово! Успешно конвертировано: {converted_count}. Пропущено бинарных: {skipped_count}.")

# --- Инструкция к запуску ---
if __name__ == '__main__':
    # Проверяем, передал ли пользователь путь через командную строку
    if len(sys.argv) > 1:
        # Берем путь из аргументов командной строки и очищаем от лишних кавычек
        TARGET_FOLDER = sys.argv[1].strip("'\"")
    else:
        # Если аргумент не передан, используем текущую папку, где лежит скрипт
        TARGET_FOLDER = os.path.dirname(os.path.abspath(__file__))

    batch_convert_stl_in_folder(TARGET_FOLDER)
