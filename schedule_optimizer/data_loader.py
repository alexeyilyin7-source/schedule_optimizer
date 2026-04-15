import pandas as pd
from typing import List, Tuple
from models import Lesson, Auditorium, TimeSlot, LessonType
def load_lessons_from_excel(file_path: str) -> Tuple[List[Lesson], List[str]]:
    """Загрузка занятий из Excel-файла ведомости"""
    errors = []
    lessons = []
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return [], [f"Ошибка чтения файла: {str(e)}"]
    required_cols = ['Дисциплина', 'Институт', 'Наименование направления подготовки',
                     'Наименование образовательной программы', 'Курс', 'Поток/учебная группа',
                     'Количество обучающихся', 'Фамилия, имя, отчество преподавателя',
                     'Вид занятия', 'Часов в семестре']
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"Отсутствует колонка: {col}")
    if errors:
        return [], errors
    lesson_type_map = {
        'Лекции': LessonType.LECTURE,
        'Практ. занятия': LessonType.PRACTICE,
        'Лаб. занятия': LessonType.LAB
    }
    for idx, row in df.iterrows():
        try:
            # Пропускаем строки-разделители
            if pd.isna(row.get('Дисциплина')) or str(row['Дисциплина']).strip() == '':
                continue
            # Определяем тип занятия
            lesson_type_str = str(row['Вид занятия']) if pd.notna(row['Вид занятия']) else 'Практ. занятия'
            lesson_type = lesson_type_map.get(lesson_type_str, LessonType.PRACTICE)
            # Определяем количество студентов
            student_count = 20
            if pd.notna(row['Количество обучающихся']):
                try:
                    student_count = int(row['Количество обучающихся'])
                except:
                    student_count = 20
            # Определяем часы в семестре
            hours = 36
            if pd.notna(row['Часов в семестре']):
                try:
                    hours = int(row['Часов в семестре'])
                except:
                    hours = 36
            lesson = Lesson(
                id=idx,
                discipline=str(row['Дисциплина'])[:200],
                institute=str(row['Институт'])[:100] if pd.notna(row['Институт']) else "Не указан",
                direction=str(row['Наименование направления подготовки'])[:200] if pd.notna(
                    row['Наименование направления подготовки']) else "Не указано",
                program=str(row['Наименование образовательной программы'])[:200] if pd.notna(
                    row['Наименование образовательной программы']) else "Не указана",
                course=int(row['Курс']) if pd.notna(row['Курс']) else 1,
                group=str(row['Поток/учебная группа'])[:100],
                group_count=1,
                student_count=student_count,
                teacher=str(row['Фамилия, имя, отчество преподавателя'])[:200],
                lesson_type=lesson_type,
                hours_per_semester=hours,
                note=str(row.get('Примечание', ''))[:200] if pd.notna(row.get('Примечание')) else ""
            )
            lessons.append(lesson)
        except Exception as e:
            errors.append(f"Ошибка в строке {idx}: {str(e)}")

    return lessons, errors


def load_auditoriums_from_excel(file_path: str) -> Tuple[List[Auditorium], List[str]]:
    """Загрузка аудиторий из Excel-файла"""
    errors = []
    auditoriums = []

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return [], [f"Ошибка чтения файла: {str(e)}"]

    for idx, row in df.iterrows():
        if pd.isna(row.get('Аудитория')):
            continue

        try:
            aud_name = str(row['Аудитория'])[:100]
            if not aud_name or aud_name == 'nan':
                continue

            # Определяем категорию
            category = "Учебная аудитория"
            if pd.notna(row.get('Категория помещения')):
                category = str(row['Категория помещения'])

            # Определяем вместимость
            seats = 30
            if pd.notna(row.get('Кол. мест')):
                try:
                    seats = int(row['Кол. мест'])
                except:
                    seats = 30

            # Определяем корпус
            building = "Главный учебный корпус"
            if pd.notna(row.get('Корпус/здание')):
                building = str(row['Корпус/здание'])

            # Определяем этаж
            floor = None
            if pd.notna(row.get('Этаж')):
                try:
                    floor = int(row['Этаж'])
                except:
                    floor = None

            auditorium = Auditorium(
                id=idx,
                name=aud_name,
                category=category,
                seats=seats,
                building=building,
                floor=floor,
                comment=str(row['Комментарий'])[:200] if pd.notna(row.get('Комментарий')) else ""
            )
            auditoriums.append(auditorium)
        except Exception as e:
            errors.append(f"Ошибка в строке {idx}: {str(e)}")

    return auditoriums, errors


def create_time_slots() -> List[TimeSlot]:
    """Создание временных слотов для занятий"""
    days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ"]
    time_pairs = [
        ("9:00", "10:30", 1),
        ("10:40", "12:10", 2),
        ("12:55", "14:25", 3),
        ("14:35", "16:05", 4),
        ("16:15", "17:45", 5),
        ("17:55", "19:25", 6)
    ]

    slots = []
    slot_id = 1
    for day in days:
        for start, end, num in time_pairs:
            slots.append(TimeSlot(
                id=slot_id,
                day=day,
                start_time=start,
                end_time=end,
                pair_number=num
            ))
            slot_id += 1

    return slots