import pandas as pd
import numpy as np
from faker import Faker
import random
import re
from collections import Counter

fake = Faker('ru_RU')

# === ДАННЫЕ ИЗ ОРИГИНАЛЬНЫХ ФАЙЛОВ (извлечены из ваших Excel) ===

# Данные для ведомости
ORIGINAL_SCHEDULE_STATS = {
    'total_rows': 5300,
    'unique_counts': {
        'Дисциплина': 765,
        'Институт': 7,
        'Наименование направления подготовки': 15,
        'Наименование образовательной программы': 40,
        'Курс': 4,
        'Поток/учебная группа': 850,
        'Количество групп': 3,
        'Количество обучающихся': 30,
        'Фамилия, имя, отчество преподавателя': 200,
        'Вид занятия': 3,
        'Часов в семестре': 25
    },
    'ratios': {
        'Дисциплина': 1 / 6.9,  # 1 уникальная на 6.9 строк
        'Институт': 1 / 757,  # 1 уникальный на 757 строк
        'Поток/учебная группа': 1 / 6.2,  # 1 уникальная на 6.2 строки
        'Преподаватель': 1 / 26.5,  # 1 уникальный на 26.5 строк
    }
}

# Данные для аудиторий
ORIGINAL_AUDITORIUM_STATS = {
    'total_rows': 201,
    'unique_counts': {
        'Аудитория': 150,
        'Категория помещения': 7,
        'Кол. мест': 30,
        'Филиал': 1,
        'Корпус/здание': 7,
        'Этаж': 8
    },
    'ratios': {
        'Аудитория': 1 / 1.34,  # 1 уникальная на 1.34 строки
        'Категория помещения': 1 / 28.7,
        'Корпус/здание': 1 / 28.7,
    }
}

# Базовые данные для генерации
INSTITUTES = ['ИЭФ', 'ИУПСиБК', 'ИОМ', 'ИГУиП', 'ИИС', 'ИМ', 'Аспирантура']
INSTITUTE_WEIGHTS = [0.25, 0.20, 0.20, 0.15, 0.10, 0.07, 0.03]

DIRECTIONS = ['Экономика', 'Менеджмент', 'Инноватика', 'Экология и природопользование',
              'Государственное и муниципальное управление', 'Политология', 'Социология',
              'Управление персоналом', 'Бизнес-информатика', 'Юриспруденция', 'Психология',
              'Прикладная информатика', 'Прикладная математика и информатика']
DIRECTION_WEIGHTS = [0.18, 0.22, 0.08, 0.08, 0.08, 0.07, 0.06, 0.06, 0.05, 0.04, 0.03, 0.03, 0.02]

PROGRAMS = ['Управленческая экономика', 'Менеджмент в киберспорте', 'Международный бизнес',
            'Технологическое брокерство', 'Устойчивое природопользование', 'Цифровое право',
            'Социальная психология в управлении', 'Управление цифровой трансформацией',
            'Экономическая безопасность и анализ бизнеса', 'Бизнес-аналитика и прогнозирование',
            'Гостиничная деятельность и ивент-сервис', 'Продюсирование рекламных коммуникаций',
            'Управление в здравоохранении', 'Менеджмент в спортивной и фитнес индустрии',
            'Менеджмент в кино и телевидении', 'Государственная политика и политическое управление']

LESSON_TYPES = ['Лекции', 'Практ. занятия', 'Лаб. занятия']
LESSON_WEIGHTS = [0.40, 0.55, 0.05]

HOURS = [4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 48, 56, 72, 76, 84, 96]

# Названия дисциплин (из оригинального файла)
DISCIPLINES = [
    'Формирование инвестиционного портфеля', 'Проектное управление в фиджитал индустрии',
    'Основы международного бизнеса', 'Экономический анализ в кибер и фиджитал спорте',
    'Эконометрика', 'Медицинское сопровождение в кибер и фиджитал спорте',
    'Антидопинговый контроль в кибер и фиджитал спорте', 'Маркетинг территорий',
    'Химия окружающей среды', 'Экологические программы и проекты',
    'Основы профессионального развития: профессиональная модель политолога',
    'Модель открытых инноваций', 'География', 'Поведение потребителей и маркетинговые коммуникации',
    'Алгоритмы решения нестандартных задач', 'Управление рисками', 'Организационно-управленческая деятельность',
    'Социальное партнерство в сфере труда', 'Социальная защита детей с ограниченными возможностями',
    'Современные методы и методики преподавания экономических дисциплин',
    'Практикумы по программированию на языках R / Python', 'Практика разработки и реализации социальных проектов',
    'Цифровая трансформация и новые технологии менеджмента', 'Информационные системы и технологии',
    'Экономика и управление инвестициями', 'Управление человеческими ресурсами',
    'Финансовый анализ банка', 'Маркетинг технологических инноваций', 'Психология бизнеса',
    'Управление международными проектами', 'Кросс-культурный менеджмент', 'Антикризисное управление'
]

# Категории аудиторий
AUDITORIUM_CATEGORIES = ['Учебная аудитория', 'Компьютерный класс', 'Лаборатория',
                         'Общего назначения', 'Актовый зал', 'Спортивный зал', 'Дистанционное проведение']
CATEGORY_WEIGHTS = [0.70, 0.15, 0.05, 0.05, 0.02, 0.02, 0.01]

BUILDINGS = ['Административный корпус', 'Главный учебный корпус', 'Лабораторный корпус',
             'Поточный корпус', 'Спортивный комплекс', 'Центр информационных технологий (БЦ)',
             'Цифровой корпус ГУУ']
FLOORS = [1, 2, 3, 4, 5, 6, 7, 8]


def generate_teacher():
    """Генерирует ФИО преподавателя"""
    return f"{fake.last_name()} {fake.first_name()[0]}.{fake.middle_name()[0]}."


def generate_group_name():
    """Генерирует название группы как в оригинале"""
    types = ['ОМ', 'ОБ', 'ОА']
    nums = ['1', '2', '3', '4', '5', '6', '10', '11', '12', '42', '43', '44', '45']
    suffixes = ['', '-s2', '-q98', '-5f', '-01', '-00', '-b4', '-b2', '-b0', '-h3', '-t1', '-w1', '-g4']

    group_type = random.choice(types)
    group_num = random.choice(nums)
    suffix = random.choice(suffixes)
    course = random.randint(1, 4)

    return f"{group_type}-{group_num}{suffix} {random.randint(20, 25)}-1-{course}к"


def generate_auditorium_name():
    """Генерирует название аудитории"""
    prefixes = ['А-', 'ГУ-', 'ЛК-', 'ПА-', 'ЦИТ-', 'А', 'ГУ', 'ЛК']
    prefix = random.choice(prefixes)
    num = random.randint(100, 999)

    if prefix in ['А-', 'ГУ-', 'ЛК-', 'ПА-', 'ЦИТ-']:
        return f"{prefix}{num}"
    else:
        return f"{prefix}{num}"


def generate_schedule_data(target_rows):
    """Генерирует данные для ведомости с сохранением пропорций"""

    # Рассчитываем количество уникальных значений (минимум 1)
    unique_disciplines = max(1, int(target_rows * ORIGINAL_SCHEDULE_STATS['ratios']['Дисциплина']))
    unique_groups = max(1, int(target_rows * ORIGINAL_SCHEDULE_STATS['ratios']['Поток/учебная группа']))
    unique_teachers = max(1, int(target_rows * ORIGINAL_SCHEDULE_STATS['ratios']['Преподаватель']))

    print(f"    Планируется уникальных:")
    print(f"      - Дисциплин: {unique_disciplines}")
    print(f"      - Групп: {unique_groups}")
    print(f"      - Преподавателей: {unique_teachers}")

    # Генерируем пулы уникальных значений
    disciplines_pool = []

    # Добавляем оригинальные дисциплины
    for d in DISCIPLINES[:min(unique_disciplines, len(DISCIPLINES))]:
        disciplines_pool.append(d)

    # Если нужно больше, добавляем с суффиксами
    suffixes = ['(продвинутый)', '(базовый)', '(спецкурс)', '(углубленный)', '(практикум)']
    while len(disciplines_pool) < unique_disciplines:
        base = random.choice(DISCIPLINES)
        suffix = random.choice(suffixes)
        disciplines_pool.append(f"{base} {suffix}")

    groups_pool = [generate_group_name() for _ in range(unique_groups)]
    teachers_pool = [generate_teacher() for _ in range(unique_teachers)]

    rows = []

    for i in range(target_rows):
        row = {
            '№ п.п.': i + 1,
            'Дисциплина': random.choice(disciplines_pool),
            'Институт': random.choices(INSTITUTES, weights=INSTITUTE_WEIGHTS, k=1)[0],
            'Наименование направления подготовки': random.choices(DIRECTIONS, weights=DIRECTION_WEIGHTS, k=1)[0],
            'Наименование образовательной программы': random.choice(PROGRAMS),
            'Курс': random.randint(1, 4),
            'Поток/учебная группа': random.choice(groups_pool),
            'Количество групп': random.randint(1, 3),
            'Количество обучающихся': random.randint(5, 40),
            'Фамилия, имя, отчество преподавателя': random.choice(teachers_pool),
            'Вид занятия': random.choices(LESSON_TYPES, weights=LESSON_WEIGHTS, k=1)[0],
            'Часов в семестре': random.choice(HOURS),
            'Фамилия, имя, отчество преподавателя, заменяющего преподавателя гр.10': generate_teacher() if random.random() < 0.05 else '',
            'Причина замены преподавателя': random.choice(
                ['Болезнь', 'Отпуск', 'Командировка', '']) if random.random() < 0.05 else '',
            'Примечание': random.choice(
                ['', 'Факультатив', 'По выбору', 'С изменениями']) if random.random() < 0.08 else ''
        }
        rows.append(row)

        if (i + 1) % 5000 == 0:
            print(f"    Сгенерировано {i + 1} строк...")

    return pd.DataFrame(rows)


def generate_auditorium_data(target_rows):
    """Генерирует данные для списка аудиторий с сохранением пропорций"""

    # Рассчитываем количество уникальных аудиторий (минимум 1)
    unique_auditoriums = max(1, int(target_rows * ORIGINAL_AUDITORIUM_STATS['ratios']['Аудитория']))

    print(f"    Планируется уникальных аудиторий: {unique_auditoriums}")

    # Генерируем пулы
    auditoriums_pool = [generate_auditorium_name() for _ in range(unique_auditoriums)]

    # Количество мест для каждой категории
    seats_by_category = {
        'Учебная аудитория': [20, 24, 26, 28, 30, 32, 36, 38, 40, 42, 48, 50, 60, 70, 80, 100, 132, 176, 192, 200],
        'Компьютерный класс': [10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 33],
        'Лаборатория': [15, 16, 18, 20, 22, 24, 25, 28],
        'Общего назначения': [10, 16, 18, 20, 30],
        'Актовый зал': [800, 1000, 5000],
        'Спортивный зал': [400],
        'Дистанционное проведение': [1000, 5000]
    }

    rows = []

    for i in range(target_rows):
        # Иногда добавляем строку-разделитель корпуса
        if random.random() < 0.03 and i > 0:
            building = random.choice(BUILDINGS)
            rows.append({
                'Аудитория': building,
                'Категория помещения': '',
                'Кол. мест': '',
                'Филиал': '',
                'Комментарий': '',
                'Ответственный': '',
                'Кафедра': '',
                'Корпус/здание': '',
                'Этаж': ''
            })

        # Генерируем основную строку
        category = random.choices(AUDITORIUM_CATEGORIES, weights=CATEGORY_WEIGHTS, k=1)[0]
        seats = random.choice(seats_by_category.get(category, [30, 40, 50]))

        # Комментарий в зависимости от категории
        comment = ''
        if category == 'Компьютерный класс':
            comment = f"{random.randint(10, 25)} ПК, TV"
        elif category == 'Лаборатория':
            comment = f"{random.choice(['Моноблок', 'ПК'])} ({random.randint(5, 15)} шт), {random.choice(['TV', 'проектор', 'экран'])}"
        elif random.random() < 0.15:
            comment = fake.sentence()

        row = {
            'Аудитория': random.choice(auditoriums_pool),
            'Категория помещения': category,
            'Кол. мест': seats,
            'Филиал': 'Государственный университет управления',
            'Комментарий': comment,
            'Ответственный': generate_teacher() if random.random() < 0.1 else '',
            'Кафедра': f"Институт {random.choice(['экономики и финансов', 'управления', 'маркетинга', 'информационных систем'])}" if random.random() < 0.25 else '',
            'Корпус/здание': random.choice(BUILDINGS),
            'Этаж': random.choice(FLOORS) if random.random() < 0.8 else ''
        }
        rows.append(row)

        if (i + 1) % 1000 == 0:
            print(f"    Сгенерировано {i + 1} строк...")

    return pd.DataFrame(rows)


def main():
    print("=" * 70)
    print("ГЕНЕРАТОР ФЕЙКОВЫХ ДАННЫХ С СОХРАНЕНИЕМ ПРОПОРЦИЙ")
    print("=" * 70)

    print("\nИсходные данные из оригинальных файлов:")
    print(f"  - Ведомость: {ORIGINAL_SCHEDULE_STATS['total_rows']:,} строк")
    print(f"  - Список аудиторий: {ORIGINAL_AUDITORIUM_STATS['total_rows']} строк")

    print("\n" + "-" * 70)
    print("ДОСТУПНЫЕ КОЭФФИЦИЕНТЫ:")
    print("-" * 70)

    # Показываем все доступные коэффициенты
    print("\n  Меньше 1 (шаг 0.1):")
    small_factors = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    for f in small_factors:
        schedule_rows = int(ORIGINAL_SCHEDULE_STATS['total_rows'] * f)
        auditorium_rows = int(ORIGINAL_AUDITORIUM_STATS['total_rows'] * f)
        print(f"    {f:4.1f}  -> Ведомость: {schedule_rows:5,} строк, Аудитории: {auditorium_rows:3} строк")

    print("\n  Равно 1:")
    print(
        f"    1.0  -> Ведомость: {ORIGINAL_SCHEDULE_STATS['total_rows']:,} строк, Аудитории: {ORIGINAL_AUDITORIUM_STATS['total_rows']} строк")

    print("\n  Больше 1 (целые числа):")
    large_factors = [2, 3, 4, 5, 10, 20, 50, 100]
    for f in large_factors:
        schedule_rows = int(ORIGINAL_SCHEDULE_STATS['total_rows'] * f)
        auditorium_rows = int(ORIGINAL_AUDITORIUM_STATS['total_rows'] * f)
        print(f"    {f:3.0f}  -> Ведомость: {schedule_rows:6,} строк, Аудитории: {auditorium_rows:4} строк")

    print("\n" + "-" * 70)
    print("  Также можно ввести ЛЮБОЕ число от 0.1 до 100")
    print("  Например: 0.15, 0.25, 0.75, 1.5, 2.5, 7.5 и т.д.")
    print("-" * 70)

    print()

    try:
        ratio = float(input("Введите коэффициент: "))
        if ratio < 0.1:
            print("Коэффициент меньше 0.1. Устанавливаю 0.1")
            ratio = 0.1
        elif ratio > 100:
            print("Коэффициент больше 100. Устанавливаю 100")
            ratio = 100
        elif ratio <= 0:
            print("Коэффициент должен быть положительным. Использую 1")
            ratio = 1
    except:
        print("Некорректный ввод. Использую коэффициент 1")
        ratio = 1

    # Округляем до 2 знаков для красоты
    ratio = round(ratio, 2)

    # Целевое количество строк
    target_schedule = max(1, int(ORIGINAL_SCHEDULE_STATS['total_rows'] * ratio))
    target_auditorium = max(1, int(ORIGINAL_AUDITORIUM_STATS['total_rows'] * ratio))

    print(f"\n" + "=" * 70)
    print(f"ВЫБРАН КОЭФФИЦИЕНТ: {ratio}")
    print("=" * 70)

    print(f"\nЦелевое количество строк:")
    print(f"  - Ведомость: {target_schedule:,} (было 5,300 × {ratio} = {5300 * ratio:.1f})")
    print(f"  - Список аудиторий: {target_auditorium} (было 201 × {ratio} = {201 * ratio:.1f})")

    # Генерация ведомости
    print("\n" + "-" * 70)
    print("ГЕНЕРАЦИЯ ВЕДОМОСТИ")
    print("-" * 70)

    schedule_df = generate_schedule_data(target_schedule)
    schedule_file = f"Ведомость_осенний_семестр_фейк_{ratio}x.xlsx"
    schedule_df.to_excel(schedule_file, index=False)

    print(f"\n✓ СОЗДАН ФАЙЛ: {schedule_file}")
    print(f"  - Строк: {len(schedule_df):,}")
    print(f"  - Колонок: {len(schedule_df.columns)}")
    print(f"  - Уникальных дисциплин: {schedule_df['Дисциплина'].nunique():,}")
    print(f"  - Уникальных групп: {schedule_df['Поток/учебная группа'].nunique():,}")
    print(f"  - Уникальных преподавателей: {schedule_df['Фамилия, имя, отчество преподавателя'].nunique():,}")

    # Генерация списка аудиторий
    print("\n" + "-" * 70)
    print("ГЕНЕРАЦИЯ СПИСКА АУДИТОРИЙ")
    print("-" * 70)

    auditorium_df = generate_auditorium_data(target_auditorium)
    auditorium_file = f"Список_аудиторий_фейк_{ratio}x.xlsx"
    auditorium_df.to_excel(auditorium_file, index=False)

    print(f"\n✓ СОЗДАН ФАЙЛ: {auditorium_file}")
    print(f"  - Строк: {len(auditorium_df):,}")
    print(f"  - Колонок: {len(auditorium_df.columns)}")
    print(f"  - Уникальных аудиторий: {auditorium_df['Аудитория'].nunique():,}")

    print("\n" + "=" * 70)
    print("ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
    print("=" * 70)
    print(f"\nСозданные файлы:")
    print(f"  1. {schedule_file}")
    print(f"  2. {auditorium_file}")

    # Показываем пример
    print("\n--- ПРИМЕР СГЕНЕРИРОВАННЫХ ДАННЫХ ---")
    print("\nВедомость (первые 3 строки):")
    print(schedule_df.head(3).to_string())
    print("\nСписок аудиторий (первые 3 строки):")
    print(auditorium_df.head(3).to_string())


if __name__ == "__main__":
    main()