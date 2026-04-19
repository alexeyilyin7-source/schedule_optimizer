import random
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from algorithms import ScheduleOptimizer
from app import app
from data_loader import create_time_slots, load_auditoriums_from_excel, load_lessons_from_excel
from models import LessonType

BASE_DIR = Path(__file__).resolve().parent.parent
client = TestClient(app)


@pytest.fixture(autouse=True)
def fixed_random_seed() -> None:
    random.seed(42)


@pytest.fixture()
def synthetic_excel_files(tmp_path: Path) -> Tuple[Path, Path, pd.DataFrame, pd.DataFrame]:
    lessons_df = pd.DataFrame(
        [
            {
                "Дисциплина": "Математика",
                "Институт": "Институт информационных технологий",
                "Наименование направления подготовки": "Прикладная информатика",
                "Наименование образовательной программы": "Информационные технологии и системная аналитика",
                "Курс": 1,
                "Поток/учебная группа": "ПИ-1",
                "Количество обучающихся": 25,
                "Фамилия, имя, отчество преподавателя": "Иванов И.И.",
                "Вид занятия": "Лекции",
                "Часов в семестре": 36,
            },
            {
                "Дисциплина": "Информатика",
                "Институт": "Институт информационных технологий",
                "Наименование направления подготовки": "Прикладная информатика",
                "Наименование образовательной программы": "Информационные технологии и системная аналитика",
                "Курс": 1,
                "Поток/учебная группа": "ПИ-1",
                "Количество обучающихся": 20,
                "Фамилия, имя, отчество преподавателя": "Петров П.П.",
                "Вид занятия": "Практ. занятия",
                "Часов в семестре": 36,
            },
            {
                "Дисциплина": "Физика",
                "Институт": "Институт информационных технологий",
                "Наименование направления подготовки": "Прикладная информатика",
                "Наименование образовательной программы": "Информационные технологии и системная аналитика",
                "Курс": 1,
                "Поток/учебная группа": "ПИ-2",
                "Количество обучающихся": 18,
                "Фамилия, имя, отчество преподавателя": "Сидоров С.С.",
                "Вид занятия": "Лаб. занятия",
                "Часов в семестре": 36,
            },
            {
                "Дисциплина": "История",
                "Институт": "Институт информационных технологий",
                "Наименование направления подготовки": "Прикладная информатика",
                "Наименование образовательной программы": "Информационные технологии и системная аналитика",
                "Курс": 1,
                "Поток/учебная группа": "ПИ-2",
                "Количество обучающихся": 18,
                "Фамилия, имя, отчество преподавателя": "Смирнов А.А.",
                "Вид занятия": "Практ. занятия",
                "Часов в семестре": 36,
            },
        ]
    )

    auditoriums_df = pd.DataFrame(
        [
            {
                "Аудитория": "101",
                "Категория помещения": "Учебная аудитория",
                "Кол. мест": 50,
                "Корпус/здание": "Главный учебный корпус",
                "Этаж": 1,
            },
            {
                "Аудитория": "202",
                "Категория помещения": "Компьютерный класс",
                "Кол. мест": 25,
                "Корпус/здание": "Главный учебный корпус",
                "Этаж": 2,
            },
            {
                "Аудитория": "303",
                "Категория помещения": "Лаборатория",
                "Кол. мест": 20,
                "Корпус/здание": "Главный учебный корпус",
                "Этаж": 3,
            },
        ]
    )

    lessons_file = tmp_path / "lessons.xlsx"
    auditoriums_file = tmp_path / "auditoriums.xlsx"
    lessons_df.to_excel(lessons_file, index=False)
    auditoriums_df.to_excel(auditoriums_file, index=False)

    return lessons_file, auditoriums_file, lessons_df, auditoriums_df


def _validate_hard_constraints(schedule: List[Dict], auditoriums_df: pd.DataFrame, lessons_df: pd.DataFrame) -> None:
    lesson_meta = {
        row["Дисциплина"]: {
            "group": row["Поток/учебная группа"],
            "teacher": row["Фамилия, имя, отчество преподавателя"],
            "students": int(row["Количество обучающихся"]),
            "lesson_type": row["Вид занятия"],
        }
        for _, row in lessons_df.iterrows()
    }
    aud_meta = {
        row["Аудитория"]: {
            "category": row["Категория помещения"],
            "seats": int(row["Кол. мест"]),
        }
        for _, row in auditoriums_df.iterrows()
    }

    teacher_slots = Counter()
    group_slots = Counter()
    auditorium_slots = Counter()

    for entry in schedule:
        lesson = lesson_meta[entry["discipline"]]
        auditorium = aud_meta[entry["auditorium"]]
        slot_key = (entry["day"], entry["pair_number"], entry["week_parity"])

        teacher_slots[(lesson["teacher"],) + slot_key] += 1
        group_slots[(lesson["group"],) + slot_key] += 1
        auditorium_slots[(entry["auditorium"],) + slot_key] += 1

        assert auditorium["seats"] >= lesson["students"], "В расписание попала аудитория с недостаточной вместимостью"

        if lesson["lesson_type"] == "Лекции":
            assert auditorium["category"] in {"Учебная аудитория", "Актовый зал"}
        elif lesson["lesson_type"] == "Лаб. занятия":
            assert auditorium["category"] in {"Компьютерный класс", "Лаборатория"}
        else:
            assert auditorium["category"] in {"Учебная аудитория", "Общего назначения", "Компьютерный класс"}

    assert max(teacher_slots.values(), default=0) == 1, "Есть конфликт преподавателя в одном слоте"
    assert max(group_slots.values(), default=0) == 1, "Есть конфликт учебной группы в одном слоте"
    assert max(auditorium_slots.values(), default=0) == 1, "Есть конфликт аудитории в одном слоте"


# -----------------------------
# Модульные тесты
# -----------------------------

def test_create_time_slots_returns_full_week_grid() -> None:
    slots = create_time_slots()

    assert len(slots) == 36
    assert slots[0].day == "ПН"
    assert slots[0].pair_number == 1
    assert slots[-1].day == "СБ"
    assert slots[-1].pair_number == 6
    assert len({(slot.day, slot.pair_number) for slot in slots}) == 36



def test_loaders_parse_valid_excel_files(synthetic_excel_files: Tuple[Path, Path, pd.DataFrame, pd.DataFrame]) -> None:
    lessons_file, auditoriums_file, _, _ = synthetic_excel_files

    lessons, lesson_errors = load_lessons_from_excel(str(lessons_file))
    auditoriums, auditorium_errors = load_auditoriums_from_excel(str(auditoriums_file))

    assert lesson_errors == []
    assert auditorium_errors == []
    assert len(lessons) == 4
    assert len(auditoriums) == 3
    assert lessons[0].lesson_type == LessonType.LECTURE
    assert auditoriums[0].seats == 50



def test_optimizer_detects_conflicts_and_mismatches(synthetic_excel_files: Tuple[Path, Path, pd.DataFrame, pd.DataFrame]) -> None:
    lessons_file, auditoriums_file, _, _ = synthetic_excel_files
    lessons, _ = load_lessons_from_excel(str(lessons_file))
    auditoriums, _ = load_auditoriums_from_excel(str(auditoriums_file))
    time_slots = create_time_slots()

    optimizer = ScheduleOptimizer(lessons, auditoriums, time_slots)
    lesson_map = {lesson.id: lesson for lesson in lessons}
    aud_map = {aud.id: aud for aud in auditoriums}
    slot_map = {slot.id: slot for slot in time_slots}

    deliberately_bad_solution = [
        (lessons[0].id, auditoriums[1].id, time_slots[0].id, "Ч"),
        (lessons[1].id, auditoriums[1].id, time_slots[0].id, "Ч"),
    ]

    fitness, violations = optimizer._calculate_fitness(deliberately_bad_solution, lesson_map, aud_map, slot_map)

    assert fitness > 0
    assert violations["group_conflict"] >= 1
    assert violations["auditorium_conflict"] >= 1
    assert violations["auditorium_mismatch"] >= 1


# -----------------------------
# Интеграционные тесты
# -----------------------------

@pytest.mark.parametrize("algorithm_name", ["genetic", "annealing", "greedy", "combined"])
def test_optimizer_algorithms_generate_valid_schedule(
    synthetic_excel_files: Tuple[Path, Path, pd.DataFrame, pd.DataFrame], algorithm_name: str
) -> None:
    lessons_file, auditoriums_file, lessons_df, auditoriums_df = synthetic_excel_files
    lessons, _ = load_lessons_from_excel(str(lessons_file))
    auditoriums, _ = load_auditoriums_from_excel(str(auditoriums_file))
    time_slots = create_time_slots()

    optimizer = ScheduleOptimizer(lessons, auditoriums, time_slots)

    if algorithm_name == "genetic":
        solution, fitness, violations, _ = optimizer.genetic_algorithm()
    elif algorithm_name == "annealing":
        base_solution, _, _, _ = optimizer.genetic_algorithm()
        solution, fitness, violations, _ = optimizer.simulated_annealing(initial_solution=base_solution)
    elif algorithm_name == "greedy":
        solution, fitness, violations, _ = optimizer.greedy_algorithm()
    else:
        result = optimizer.run_combined_optimization()
        best = result["best"]
        solution, fitness, violations = best["solution"], best["fitness"], best["violations"]

    assert len(solution) == len(lessons)
    assert fitness >= 0
    assert violations["teacher_conflict"] == 0
    assert violations["group_conflict"] == 0
    assert violations["auditorium_conflict"] == 0
    assert violations["auditorium_mismatch"] == 0

    lesson_map = {lesson.id: lesson for lesson in lessons}
    aud_map = {aud.id: aud for aud in auditoriums}
    slot_map = {slot.id: slot for slot in time_slots}

    api_like_schedule = [
        {
            "discipline": lesson_map[lesson_id].discipline,
            "auditorium": aud_map[aud_id].name,
            "day": slot_map[slot_id].day,
            "pair_number": slot_map[slot_id].pair_number,
            "week_parity": week_parity,
        }
        for lesson_id, aud_id, slot_id, week_parity in solution
    ]
    _validate_hard_constraints(api_like_schedule, auditoriums_df, lessons_df)



def test_optimize_endpoint_returns_schedule_without_critical_violations(
    synthetic_excel_files: Tuple[Path, Path, pd.DataFrame, pd.DataFrame]
) -> None:
    lessons_file, auditoriums_file, lessons_df, auditoriums_df = synthetic_excel_files

    with lessons_file.open("rb") as schedule_fp, auditoriums_file.open("rb") as auditorium_fp:
        response = client.post(
            "/optimize",
            files={
                "schedule_file": (
                    "lessons.xlsx",
                    schedule_fp,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                "auditorium_file": (
                    "auditoriums.xlsx",
                    auditorium_fp,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert "error" not in payload
    assert len(payload["schedule"]) == len(lessons_df)
    assert payload["fitness_score"] >= 0
    assert payload["algorithm_used"] in {"genetic", "annealing", "greedy", "combined"}
    assert payload["violations"]["teacher_conflict"] == 0
    assert payload["violations"]["group_conflict"] == 0
    assert payload["violations"]["auditorium_conflict"] == 0
    assert payload["violations"]["auditorium_mismatch"] == 0

    _validate_hard_constraints(payload["schedule"], auditoriums_df, lessons_df)


# -----------------------------
# Нагрузочный тест
# -----------------------------

def test_optimize_endpoint_withstands_repeated_requests(
    synthetic_excel_files: Tuple[Path, Path, pd.DataFrame, pd.DataFrame]
) -> None:
    lessons_file, auditoriums_file, lessons_df, auditoriums_df = synthetic_excel_files

    requests_count = 10
    successful_requests = 0
    durations: List[float] = []

    for iteration in range(requests_count):
        random.seed(100 + iteration)
        started_at = time.perf_counter()
        with lessons_file.open("rb") as schedule_fp, auditoriums_file.open("rb") as auditorium_fp:
            response = client.post(
                "/optimize",
                files={
                    "schedule_file": (
                        f"lessons_{iteration}.xlsx",
                        schedule_fp,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ),
                    "auditorium_file": (
                        f"auditoriums_{iteration}.xlsx",
                        auditorium_fp,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ),
                },
            )
        durations.append(time.perf_counter() - started_at)

        assert response.status_code == 200
        payload = response.json()
        assert "error" not in payload
        assert payload["violations"]["teacher_conflict"] == 0
        assert payload["violations"]["group_conflict"] == 0
        assert payload["violations"]["auditorium_conflict"] == 0
        assert payload["violations"]["auditorium_mismatch"] == 0
        _validate_hard_constraints(payload["schedule"], auditoriums_df, lessons_df)
        successful_requests += 1

    assert successful_requests == requests_count
    assert max(durations) < 2.0
    assert sum(durations) < 10.0
