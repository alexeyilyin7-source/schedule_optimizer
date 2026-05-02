#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Комплексное тестирование Автоматизированной системы составления расписания.
Включает итоговое сравнение результатов тестирования комбинаторного алгоритма (движок оптимизации).
"""

import json
import os
import random
import sys
import time
import unittest
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "tests" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models import Lesson, Auditorium, TimeSlot, LessonType
from data_loader import load_lessons_from_excel, load_auditoriums_from_excel, create_time_slots
from algorithms import ScheduleOptimizer
from db_manager import ScheduleDB

random.seed(42)
np.random.seed(42)


def _project_file(*names: str) -> Optional[Path]:
    for name in names:
        candidate = PROJECT_ROOT / name
        if candidate.exists():
            return candidate
    return None


def _save_table(df: pd.DataFrame, filename: str) -> None:
    csv_path = OUTPUT_DIR / f"{filename}.csv"
    xlsx_path = OUTPUT_DIR / f"{filename}.xlsx"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    try:
        df.to_excel(xlsx_path, index=False)
    except Exception:
        pass


def _print_table(df: pd.DataFrame, title: str) -> None:
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"  {title}")
    print(f"{separator}")
    print(df.to_string(index=False))


def generate_test_data_if_needed():
    schedule_file = _project_file(
        "Ведомость_осенний_семестр_фейк_1.0x.xlsx",
        "Ведомость_осенний_семестр_фейк_1x.xlsx",
        "Ведомость_осенний_семестр_фейк_1.xlsx",
    )
    auditorium_file = _project_file(
        "Список_аудиторий_фейк_1.0x.xlsx",
        "Список_аудиторий_фейк_1x.xlsx",
        "Список_аудиторий_фейк_1.xlsx",
    )

    if schedule_file and auditorium_file:
        print(f"  ✓ Найдены входные файлы: {schedule_file.name}, {auditorium_file.name}")
        return schedule_file, auditorium_file

    print("  ⚠️ Файлы не найдены, будут использованы синтетические данные")
    return None, None


class TestScheduleSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print("  МОДУЛЬНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ")
        print("=" * 70)

        schedule_file, auditorium_file = generate_test_data_if_needed()

        if schedule_file and auditorium_file:
            cls.lessons, cls.lesson_errors = load_lessons_from_excel(str(schedule_file))
            cls.auditoriums, cls.auditorium_errors = load_auditoriums_from_excel(str(auditorium_file))

            # Ограничиваем количество для тестирования
            cls.lessons = cls.lessons[:200] if len(cls.lessons) > 200 else cls.lessons
            cls.auditoriums = cls.auditoriums[:100] if len(cls.auditoriums) > 100 else cls.auditoriums
        else:
            cls.lessons, cls.lesson_errors = [], []
            cls.auditoriums, cls.auditorium_errors = [], []

        cls.time_slots = create_time_slots()

        if not cls.lessons:
            print("  ⚠️ Создаются синтетические данные для тестирования")
            cls.lessons = cls._create_synthetic_lessons()
            cls.auditoriums = cls._create_synthetic_auditoriums()

        cls.test_lessons = cls.lessons[:50]
        cls.test_auditoriums = cls.auditoriums[:30]

        print(f"  ✓ Загружено занятий: {len(cls.lessons)}")
        print(f"  ✓ Загружено аудиторий: {len(cls.auditoriums)}")
        print(f"  ✓ Создано временных слотов: {len(cls.time_slots)}")

    @classmethod
    def _create_synthetic_lessons(cls) -> List[Lesson]:
        lessons = []
        teachers = ["Иванов И.И.", "Петров П.П.", "Сидоров С.С.", "Кузнецова А.А.", "Смирнова Е.В."]
        groups = ["ОМ-1", "ОБ-2", "ОА-3", "ОМ-4", "ОБ-5"]
        disciplines = ["Математика", "Физика", "Информатика", "Экономика", "Менеджмент"]
        institutes = ["ИЭФ", "ИОМ", "ИИС", "ИУПСиБК", "ИМ"]
        directions = ["Экономика", "Менеджмент", "Информатика", "Управление"]
        programs = ["Бакалавриат", "Магистратура"]

        for i in range(80):
            lessons.append(Lesson(
                id=i,
                discipline=np.random.choice(disciplines),
                institute=np.random.choice(institutes),
                direction=np.random.choice(directions),
                program=np.random.choice(programs),
                course=int(np.random.randint(1, 5)),
                group=np.random.choice(groups),
                group_count=1,
                student_count=int(np.random.randint(15, 40)),
                teacher=np.random.choice(teachers),
                lesson_type=np.random.choice([LessonType.LECTURE, LessonType.PRACTICE, LessonType.LAB]),
                hours_per_semester=int(np.random.choice([36, 48, 72, 96])),
                note="",
            ))
        return lessons

    @classmethod
    def _create_synthetic_auditoriums(cls) -> List[Auditorium]:
        auditoriums = []
        categories = ["Учебная аудитория", "Компьютерный класс", "Лаборатория", "Актовый зал"]
        buildings = ["Главный учебный корпус", "Лабораторный корпус", "Поточный корпус"]

        for i in range(30):
            auditoriums.append(Auditorium(
                id=i,
                name=f"А-{100 + i}",
                category=np.random.choice(categories),
                seats=int(np.random.choice([20, 30, 40, 50, 60, 80, 100])),
                building=np.random.choice(buildings),
                floor=int(np.random.randint(1, 7)),
                comment="",
            ))
        return auditoriums

    def test_data_loader(self):
        print("\n" + "-" * 50)
        print("  ТЕСТ 1: Проверка загрузки данных")
        print("-" * 50)

        self.assertTrue(len(self.test_lessons) > 0)
        self.assertTrue(len(self.test_auditoriums) > 0)
        self.assertTrue(len(self.time_slots) > 0)

        stats_df = pd.DataFrame([
            {"Показатель": "Всего занятий", "Значение": len(self.lessons)},
            {"Показатель": "Всего аудиторий", "Значение": len(self.auditoriums)},
            {"Показатель": "Всего временных слотов", "Значение": len(self.time_slots)},
            {"Показатель": "Уникальных преподавателей", "Значение": len({l.teacher for l in self.test_lessons})},
            {"Показатель": "Уникальных групп", "Значение": len({l.group for l in self.test_lessons})},
        ])
        _print_table(stats_df, "ТАБЛИЦА 1 - Статистика загрузки данных")
        _save_table(stats_df, "01_data_loader_stats")

    def test_database_operations(self):
        print("\n" + "-" * 50)
        print("  ТЕСТ 2: Проверка модуля базы данных")
        print("-" * 50)

        db_path = OUTPUT_DIR / "test_schedule_runtime.db"
        if db_path.exists():
            db_path.unlink()

        db = ScheduleDB(str(db_path))
        test_records = [
            {
                "curriculum_id": 1,
                "auditorium_id": 1,
                "time_slot_id": 1,
                "discipline_id": 1,
                "week_parity": "Ч",
                "created_at": "2026-04-22 10:00:00",
                "is_cancelled": 0,
                "cancel_reason": None,
            },
            {
                "curriculum_id": 2,
                "auditorium_id": 2,
                "time_slot_id": 2,
                "discipline_id": 2,
                "week_parity": "НЧ",
                "created_at": "2026-04-22 10:05:00",
                "is_cancelled": 0,
                "cancel_reason": None,
            },
        ]
        db.save_schedule(test_records)
        results = db.get_schedule()

        self.assertEqual(len(results), 2)
        print(f"  ✓ В БД сохранено и прочитано записей: {len(results)}")

    def test_fitness_function(self):
        print("\n" + "-" * 50)
        print("  ТЕСТ 3: Проверка fitness-функции")
        print("-" * 50)

        optimizer = ScheduleOptimizer(self.test_lessons[:20], self.test_auditoriums, self.time_slots)
        individual = optimizer._create_individual()

        lesson_map = {lesson.id: lesson for lesson in optimizer.lessons}
        aud_map = {aud.id: aud for aud in optimizer.auditoriums}
        slot_map = {slot.id: slot for slot in optimizer.time_slots}
        fitness, violations = optimizer._calculate_fitness(individual, lesson_map, aud_map, slot_map)

        self.assertIsInstance(fitness, (int, float))
        self.assertGreaterEqual(fitness, 0)
        print(f"  ✓ Fitness рассчитан: {fitness:.2f}")

    def test_all_algorithms_comparison(self):
        """
        ТЕСТ 4: Итоговое сравнение всех алгоритмов (движок оптимизации)
        """
        print("\n" + "=" * 70)
        print("  ИТОГОВОЕ СРАВНЕНИЕ ВСЕХ АЛГОРИТМОВ (ДВИЖОК ОПТИМИЗАЦИИ)")
        print("=" * 70)

        # Используем первые 40 занятий для тестирования
        test_lessons = self.test_lessons[:40]
        optimizer = ScheduleOptimizer(test_lessons, self.test_auditoriums, self.time_slots)

        results_list = []
        total_start = time.time()

        # 1. Жадный алгоритм
        print("\n  [1/4] Запуск ЖАДНОГО АЛГОРИТМА...")
        start_time = time.time()
        greedy_solution, greedy_fitness, greedy_viol, greedy_time = optimizer.greedy_algorithm()
        greedy_elapsed = time.time() - start_time

        # Подсчет нарушений
        greedy_hard_violations = (
                greedy_viol.get("teacher_conflict", 0) +
                greedy_viol.get("group_conflict", 0) +
                greedy_viol.get("auditorium_conflict", 0)
        )
        greedy_soft_violations = (
                greedy_viol.get("auditorium_mismatch", 0) +
                greedy_viol.get("windows", 0) +
                greedy_viol.get("load_imbalance", 0) +
                greedy_viol.get("teacher_preference", 0)
        )

        results_list.append({
            "Алгоритм": "Жадный алгоритм",
            "Fitness": round(float(greedy_fitness), 4),
            "Штраф": round(float(sum(greedy_viol.values())), 2),
            "Время (сек)": round(greedy_elapsed, 2),
            "Жестких нарушений": int(greedy_hard_violations),
            "Мягких нарушений": int(greedy_soft_violations),
        })

        # 2. Генетический алгоритм
        print("  [2/4] Запуск ГЕНЕТИЧЕСКОГО АЛГОРИТМА...")
        start_time = time.time()
        ga_solution, ga_fitness, ga_viol, ga_time = optimizer.genetic_algorithm()
        ga_elapsed = time.time() - start_time

        ga_hard_violations = (
                ga_viol.get("teacher_conflict", 0) +
                ga_viol.get("group_conflict", 0) +
                ga_viol.get("auditorium_conflict", 0)
        )
        ga_soft_violations = (
                ga_viol.get("auditorium_mismatch", 0) +
                ga_viol.get("windows", 0) +
                ga_viol.get("load_imbalance", 0) +
                ga_viol.get("teacher_preference", 0)
        )

        results_list.append({
            "Алгоритм": "Генетический алгоритм",
            "Fitness": round(float(ga_fitness), 4),
            "Штраф": round(float(sum(ga_viol.values())), 2),
            "Время (сек)": round(ga_elapsed, 2),
            "Жестких нарушений": int(ga_hard_violations),
            "Мягких нарушений": int(ga_soft_violations),
        })

        # 3. Алгоритм имитации отжига
        print("  [3/4] Запуск АЛГОРИТМА ИМИТАЦИИ ОТЖИГА...")
        start_time = time.time()
        sa_solution, sa_fitness, sa_viol, sa_time = optimizer.simulated_annealing(
            initial_solution=ga_solution if ga_solution else None,
            max_iterations=1200
        )
        sa_elapsed = time.time() - start_time

        sa_hard_violations = (
                sa_viol.get("teacher_conflict", 0) +
                sa_viol.get("group_conflict", 0) +
                sa_viol.get("auditorium_conflict", 0)
        )
        sa_soft_violations = (
                sa_viol.get("auditorium_mismatch", 0) +
                sa_viol.get("windows", 0) +
                sa_viol.get("load_imbalance", 0) +
                sa_viol.get("teacher_preference", 0)
        )

        results_list.append({
            "Алгоритм": "Имитация отжига",
            "Fitness": round(float(sa_fitness), 4),
            "Штраф": round(float(sum(sa_viol.values())), 2),
            "Время (сек)": round(sa_elapsed, 2),
            "Жестких нарушений": int(sa_hard_violations),
            "Мягких нарушений": int(sa_soft_violations),
        })

        # 4. Комбинированный алгоритм
        print("  [4/4] Запуск КОМБИНИРОВАННОГО АЛГОРИТМА...")
        start_time = time.time()
        combined_result = optimizer.run_combined_optimization()
        combined_elapsed = time.time() - start_time

        best = combined_result["best"]
        combined_fitness = best["fitness"]
        combined_viol = best["violations"]

        combined_hard_violations = (
                combined_viol.get("teacher_conflict", 0) +
                combined_viol.get("group_conflict", 0) +
                combined_viol.get("auditorium_conflict", 0)
        )
        combined_soft_violations = (
                combined_viol.get("auditorium_mismatch", 0) +
                combined_viol.get("windows", 0) +
                combined_viol.get("load_imbalance", 0) +
                combined_viol.get("teacher_preference", 0)
        )

        results_list.append({
            "Алгоритм": "Комбинированный",
            "Fitness": round(float(combined_fitness), 4),
            "Штраф": round(float(sum(combined_viol.values())), 2),
            "Время (сек)": round(combined_elapsed, 2),
            "Жестких нарушений": int(combined_hard_violations),
            "Мягких нарушений": int(combined_soft_violations),
        })

        total_elapsed = time.time() - total_start

        # Создаем DataFrame и выводим результаты
        df = pd.DataFrame(results_list)

        print(f"\n{'=' * 70}")
        print(f"  ОПТИМИЗАЦИЯ ЗАВЕРШЕНА")
        print(f"{'=' * 70}")
        print(f"\n  ИТОГОВОЕ СРАВНЕНИЕ\n")
        _print_table(df, "ТАБЛИЦА 9 - Итоговое сравнение алгоритмов")

        # Выводим также в формате, как на скриншоте
        print(f"\n{'=' * 70}")
        print(f"  Таблица сравнения:")
        print(f"{'=' * 70}")
        for _, row in df.iterrows():
            print(
                f"  {row['Алгоритм']:25s} | {row['Fitness']:.4f} | {row['Штраф']:.2f} | {row['Время (сек)']:.2f} | {row['Жестких нарушений']} | {row['Мягких нарушений']}")

        print(f"\n  Общее время: {total_elapsed:.2f} сек")
        print(f"{'=' * 70}\n")

        # Сохраняем результаты
        _save_table(df, "09_final_algorithm_comparison")

        # Проверяем, что у нас есть результаты для всех алгоритмов
        self.assertEqual(len(results_list), 4, "Должны быть результаты для всех 4 алгоритмов")

        # Проверяем, что хотя бы один алгоритм нашел решение
        self.assertTrue(
            any(r["Fitness"] != float("inf") for r in results_list),
            "Хотя бы один алгоритм должен найти решение"
        )

        # Выделяем лучший алгоритм
        best_algo = min(results_list, key=lambda x: x["Fitness"])
        print(f"  🏆 ЛУЧШИЙ АЛГОРИТМ: {best_algo['Алгоритм']} (Fitness = {best_algo['Fitness']:.4f})")

        return df


def run_full_test_suite():
    """
    Запуск полного набора тестов с итоговым сравнением
    """
    print("\n" + "=" * 70)
    print("  АВТОМАТИЗИРОВАННАЯ СИСТЕМА СОСТАВЛЕНИЯ РАСПИСАНИЯ")
    print("  КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ")
    print("=" * 70)

    # Загружаем данные
    schedule_file, auditorium_file = generate_test_data_if_needed()

    if schedule_file and auditorium_file:
        lessons, lesson_errors = load_lessons_from_excel(str(schedule_file))
        auditoriums, auditorium_errors = load_auditoriums_from_excel(str(auditorium_file))
        lessons = lessons[:100]
        auditoriums = auditoriums[:50]
    else:
        lessons = TestScheduleSystem._create_synthetic_lessons()
        auditoriums = TestScheduleSystem._create_synthetic_auditoriums()

    time_slots = create_time_slots()

    print(f"\n  Данные для тестирования:")
    print(f"    - Занятий: {len(lessons)}")
    print(f"    - Аудиторий: {len(auditoriums)}")
    print(f"    - Временных слотов: {len(time_slots)}")

    # Создаем оптимизатор
    optimizer = ScheduleOptimizer(lessons[:40], auditoriums, time_slots)

    results_list = []
    total_start = time.time()

    # 1. Жадный алгоритм
    print("\n  [1/4] Запуск ЖАДНОГО АЛГОРИТМА...")
    start_time = time.time()
    greedy_solution, greedy_fitness, greedy_viol, _ = optimizer.greedy_algorithm()
    greedy_elapsed = time.time() - start_time

    greedy_hard = sum([
        greedy_viol.get("teacher_conflict", 0),
        greedy_viol.get("group_conflict", 0),
        greedy_viol.get("auditorium_conflict", 0)
    ])
    greedy_soft = sum([
        greedy_viol.get("auditorium_mismatch", 0),
        greedy_viol.get("windows", 0),
        greedy_viol.get("load_imbalance", 0),
        greedy_viol.get("teacher_preference", 0)
    ])

    results_list.append({
        "Алгоритм": "Жадный алгоритм",
        "Fitness": round(float(greedy_fitness), 4),
        "Штраф": round(float(sum(greedy_viol.values())), 2),
        "Время (сек)": round(greedy_elapsed, 2),
        "Жестких нарушений": int(greedy_hard),
        "Мягких нарушений": int(greedy_soft),
    })

    # 2. Генетический алгоритм
    print("  [2/4] Запуск ГЕНЕТИЧЕСКОГО АЛГОРИТМА...")
    start_time = time.time()
    ga_solution, ga_fitness, ga_viol, _ = optimizer.genetic_algorithm()
    ga_elapsed = time.time() - start_time

    ga_hard = sum([
        ga_viol.get("teacher_conflict", 0),
        ga_viol.get("group_conflict", 0),
        ga_viol.get("auditorium_conflict", 0)
    ])
    ga_soft = sum([
        ga_viol.get("auditorium_mismatch", 0),
        ga_viol.get("windows", 0),
        ga_viol.get("load_imbalance", 0),
        ga_viol.get("teacher_preference", 0)
    ])

    results_list.append({
        "Алгоритм": "Генетический алгоритм",
        "Fitness": round(float(ga_fitness), 4),
        "Штраф": round(float(sum(ga_viol.values())), 2),
        "Время (сек)": round(ga_elapsed, 2),
        "Жестких нарушений": int(ga_hard),
        "Мягких нарушений": int(ga_soft),
    })

    # 3. Имитация отжига
    print("  [3/4] Запуск АЛГОРИТМА ИМИТАЦИИ ОТЖИГА...")
    start_time = time.time()
    sa_solution, sa_fitness, sa_viol, _ = optimizer.simulated_annealing(
        initial_solution=ga_solution if ga_solution else None
    )
    sa_elapsed = time.time() - start_time

    sa_hard = sum([
        sa_viol.get("teacher_conflict", 0),
        sa_viol.get("group_conflict", 0),
        sa_viol.get("auditorium_conflict", 0)
    ])
    sa_soft = sum([
        sa_viol.get("auditorium_mismatch", 0),
        sa_viol.get("windows", 0),
        sa_viol.get("load_imbalance", 0),
        sa_viol.get("teacher_preference", 0)
    ])

    results_list.append({
        "Алгоритм": "Имитация отжига",
        "Fitness": round(float(sa_fitness), 4),
        "Штраф": round(float(sum(sa_viol.values())), 2),
        "Время (сек)": round(sa_elapsed, 2),
        "Жестких нарушений": int(sa_hard),
        "Мягких нарушений": int(sa_soft),
    })

    # 4. Комбинированный
    print("  [4/4] Запуск КОМБИНИРОВАННОГО АЛГОРИТМА...")
    start_time = time.time()
    combined_result = optimizer.run_combined_optimization()
    combined_elapsed = time.time() - start_time

    best = combined_result["best"]
    combined_fitness = best["fitness"]
    combined_viol = best["violations"]

    combined_hard = sum([
        combined_viol.get("teacher_conflict", 0),
        combined_viol.get("group_conflict", 0),
        combined_viol.get("auditorium_conflict", 0)
    ])
    combined_soft = sum([
        combined_viol.get("auditorium_mismatch", 0),
        combined_viol.get("windows", 0),
        combined_viol.get("load_imbalance", 0),
        combined_viol.get("teacher_preference", 0)
    ])

    results_list.append({
        "Алгоритм": "Комбинированный",
        "Fitness": round(float(combined_fitness), 4),
        "Штраф": round(float(sum(combined_viol.values())), 2),
        "Время (сек)": round(combined_elapsed, 2),
        "Жестких нарушений": int(combined_hard),
        "Мягких нарушений": int(combined_soft),
    })

    total_elapsed = time.time() - total_start

    # Вывод результатов
    df = pd.DataFrame(results_list)

    print(f"\n{'=' * 70}")
    print(f"  ОПТИМИЗАЦИЯ ЗАВЕРШЕНА")
    print(f"{'=' * 70}")
    print(f"\n  ИТОГОВОЕ СРАВНЕНИЕ\n")
    print(df.to_string(index=False))

    print(f"\n{'=' * 70}")
    print(f"  Таблица сравнения:")
    print(f"{'=' * 70}")
    for _, row in df.iterrows():
        print(
            f"  {row['Алгоритм']:25s} | {row['Fitness']:.4f} | {row['Штраф']:.2f} | {row['Время (сек)']:.2f} | {row['Жестких нарушений']} | {row['Мягких нарушений']}")

    print(f"\n  Общее время: {total_elapsed:.2f} сек")

    # Определяем лучший алгоритм
    best_algo = min(results_list, key=lambda x: x["Fitness"])
    print(f"\n  🏆 ЛУЧШИЙ АЛГОРИТМ: {best_algo['Алгоритм']}")
    print(f"     Fitness: {best_algo['Fitness']:.4f}")
    print(f"     Время: {best_algo['Время (сек)']:.2f} сек")
    print(f"     Жестких нарушений: {best_algo['Жестких нарушений']}")
    print(f"     Мягких нарушений: {best_algo['Мягких нарушений']}")

    print(f"\n{'=' * 70}\n")

    _save_table(df, "09_final_algorithm_comparison")

    return df


if __name__ == "__main__":
    # Запускаем полное тестирование с итоговым сравнением
    run_full_test_suite()