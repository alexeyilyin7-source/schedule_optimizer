import math
import random
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from models import Auditorium, Lesson, LessonType, TimeSlot

ScheduleVector = List[Tuple[int, int, int, str]]


class ScheduleOptimizer:
    def __init__(self, lessons: List[Lesson], auditoriums: List[Auditorium], time_slots: List[TimeSlot]):
        self.lessons = lessons
        self.auditoriums = auditoriums
        self.time_slots = time_slots
        self.days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ"]

        self.population_size = 24
        self.generations = 35
        self.mutation_rate = 0.10
        self.crossover_rate = 0.80

        self.weights = {
            "teacher_conflict": 1000.0,
            "group_conflict": 1000.0,
            "auditorium_conflict": 1000.0,
            "auditorium_mismatch": 200.0,
            "windows": 50.0,
            "load_imbalance": 30.0,
            "teacher_preference": 20.0,
            "even_odd_violation": 15.0,
        }

        self.auditoriums_by_category = defaultdict(list)
        for aud in self.auditoriums:
            self.auditoriums_by_category[aud.category].append(aud)

        self.teacher_preferences = self._generate_teacher_preferences()

    def _generate_teacher_preferences(self) -> Dict[str, Dict]:
        preferences: Dict[str, Dict] = {}
        for teacher in {lesson.teacher for lesson in self.lessons}:
            preferences[teacher] = {"max_pairs_per_day": 6}

        for teacher in preferences:
            if random.random() < 0.25:
                preferences[teacher]["avoid_days"] = random.sample(self.days, k=1)
                preferences[teacher]["max_pairs_per_day"] = random.choice([4, 5, 6])
        return preferences

    def _allowed_categories(self, lesson: Lesson) -> List[str]:
        if lesson.lesson_type == LessonType.LECTURE:
            return ["Учебная аудитория", "Актовый зал"]
        if lesson.lesson_type == LessonType.LAB:
            return ["Компьютерный класс", "Лаборатория"]
        return ["Учебная аудитория", "Общего назначения", "Компьютерный класс"]

    def _get_auditorium_for_lesson(self, lesson: Lesson) -> Optional[Auditorium]:
        suitable: List[Auditorium] = []
        for category in self._allowed_categories(lesson):
            for aud in self.auditoriums_by_category.get(category, []):
                if aud.seats >= lesson.student_count:
                    suitable.append(aud)
        if suitable:
            return random.choice(suitable)
        return random.choice(self.auditoriums) if self.auditoriums else None

    def _create_individual(self) -> ScheduleVector:
        individual: ScheduleVector = []
        used_teacher = set()
        used_group = set()
        used_aud = set()

        for lesson in sorted(self.lessons, key=lambda x: (x.lesson_type != LessonType.LECTURE, -x.student_count)):
            aud = self._get_auditorium_for_lesson(lesson)
            if aud is None or not self.time_slots:
                continue

            for _ in range(40):
                slot = random.choice(self.time_slots)
                parity = random.choice(["Ч", "НЧ"])
                key_teacher = (lesson.teacher, slot.day, slot.pair_number, parity)
                key_group = (lesson.group, slot.day, slot.pair_number, parity)
                key_aud = (aud.name, slot.day, slot.pair_number, parity)
                if key_teacher in used_teacher or key_group in used_group or key_aud in used_aud:
                    continue

                used_teacher.add(key_teacher)
                used_group.add(key_group)
                used_aud.add(key_aud)
                individual.append((lesson.id, aud.id, slot.id, parity))
                break
            else:
                slot = random.choice(self.time_slots)
                parity = random.choice(["Ч", "НЧ"])
                individual.append((lesson.id, aud.id, slot.id, parity))

        return individual

    def _calculate_fitness(self, individual: ScheduleVector, lesson_map: Dict[int, Lesson], aud_map: Dict[int, Auditorium], slot_map: Dict[int, TimeSlot]) -> Tuple[float, Dict[str, float]]:
        violations = {
            "teacher_conflict": 0.0,
            "group_conflict": 0.0,
            "auditorium_conflict": 0.0,
            "auditorium_mismatch": 0.0,
            "windows": 0.0,
            "load_imbalance": 0.0,
            "teacher_preference": 0.0,
            "even_odd_violation": 0.0,
        }

        teacher_slots = set()
        group_slots = set()
        aud_slots = set()

        teacher_daily_load = defaultdict(lambda: defaultdict(int))
        group_daily_pairs = defaultdict(lambda: defaultdict(list))

        for lesson_id, aud_id, slot_id, week_parity in individual:
            lesson = lesson_map.get(lesson_id)
            aud = aud_map.get(aud_id)
            slot = slot_map.get(slot_id)
            if not lesson or not aud or not slot:
                continue

            teacher_key = (lesson.teacher, slot.day, slot.pair_number, week_parity)
            group_key = (lesson.group, slot.day, slot.pair_number, week_parity)
            aud_key = (aud.name, slot.day, slot.pair_number, week_parity)

            if teacher_key in teacher_slots:
                violations["teacher_conflict"] += 1
            teacher_slots.add(teacher_key)

            if group_key in group_slots:
                violations["group_conflict"] += 1
            group_slots.add(group_key)

            if aud_key in aud_slots:
                violations["auditorium_conflict"] += 1
            aud_slots.add(aud_key)

            if lesson.lesson_type == LessonType.LECTURE and aud.category not in ["Учебная аудитория", "Актовый зал"]:
                violations["auditorium_mismatch"] += 1
            if lesson.lesson_type == LessonType.LAB and aud.category not in ["Компьютерный класс", "Лаборатория"]:
                violations["auditorium_mismatch"] += 1
            if aud.seats < lesson.student_count:
                violations["auditorium_mismatch"] += 1

            teacher_daily_load[lesson.teacher][slot.day] += 1
            group_daily_pairs[lesson.group][slot.day].append(slot.pair_number)

        for teacher, days in teacher_daily_load.items():
            pref = self.teacher_preferences.get(teacher, {})
            max_pairs = pref.get("max_pairs_per_day", 6)
            avoid_days = pref.get("avoid_days", [])
            for day, load in days.items():
                if load > max_pairs:
                    violations["teacher_preference"] += load - max_pairs
                if day in avoid_days:
                    violations["teacher_preference"] += load

        for days in group_daily_pairs.values():
            for pairs in days.values():
                pairs = sorted(set(pairs))
                if len(pairs) > 1:
                    gaps = sum(max(0, pairs[i + 1] - pairs[i] - 1) for i in range(len(pairs) - 1))
                    violations["windows"] += gaps

        load_values = [load for teacher_days in teacher_daily_load.values() for load in teacher_days.values()]
        if load_values:
            avg = sum(load_values) / len(load_values)
            violations["load_imbalance"] = sum(abs(v - avg) for v in load_values)

        total_fitness = sum(self.weights[key] * value for key, value in violations.items())
        return total_fitness, violations

    def _selection(self, population: List[ScheduleVector], fitnesses: List[float]) -> List[ScheduleVector]:
        selected = []
        for _ in range(len(population)):
            candidates = random.sample(range(len(population)), k=min(3, len(population)))
            winner_index = min(candidates, key=lambda idx: fitnesses[idx])
            selected.append(population[winner_index][:])
        return selected

    def _crossover(self, parent1: ScheduleVector, parent2: ScheduleVector) -> Tuple[ScheduleVector, ScheduleVector]:
        if random.random() > self.crossover_rate or len(parent1) <= 1 or len(parent2) <= 1:
            return parent1[:], parent2[:]
        point = random.randint(1, min(len(parent1), len(parent2)) - 1)
        return parent1[:point] + parent2[point:], parent2[:point] + parent1[point:]

    def _mutate(self, individual: ScheduleVector) -> ScheduleVector:
        if not individual or not self.time_slots:
            return individual

        mutated = individual[:]
        lesson_lookup = {lesson.id: lesson for lesson in self.lessons}
        for idx, item in enumerate(mutated):
            if random.random() >= self.mutation_rate:
                continue
            lesson_id, _, _, _ = item
            lesson = lesson_lookup.get(lesson_id)
            if not lesson:
                continue
            aud = self._get_auditorium_for_lesson(lesson)
            slot = random.choice(self.time_slots)
            parity = random.choice(["Ч", "НЧ"])
            if aud:
                mutated[idx] = (lesson_id, aud.id, slot.id, parity)
        return mutated

    def genetic_algorithm(self) -> Tuple[ScheduleVector, float, Dict[str, float], float]:
        start = time.time()
        if not self.lessons or not self.auditoriums or not self.time_slots:
            return [], float("inf"), {}, 0.0

        lesson_map = {lesson.id: lesson for lesson in self.lessons}
        aud_map = {aud.id: aud for aud in self.auditoriums}
        slot_map = {slot.id: slot for slot in self.time_slots}

        population = [self._create_individual() for _ in range(self.population_size)]
        population = [p for p in population if p]
        if not population:
            return [], float("inf"), {}, 0.0

        best_solution: ScheduleVector = []
        best_fitness = float("inf")
        best_violations: Dict[str, float] = {}

        for _ in range(self.generations):
            fitnesses = []
            for individual in population:
                fitness, violations = self._calculate_fitness(individual, lesson_map, aud_map, slot_map)
                fitnesses.append(fitness)
                if fitness < best_fitness:
                    best_solution = individual[:]
                    best_fitness = fitness
                    best_violations = violations

            selected = self._selection(population, fitnesses)
            next_population: List[ScheduleVector] = []
            for idx in range(0, len(selected), 2):
                if idx + 1 < len(selected):
                    child1, child2 = self._crossover(selected[idx], selected[idx + 1])
                    next_population.extend([self._mutate(child1), self._mutate(child2)])
                else:
                    next_population.append(self._mutate(selected[idx]))

            if best_solution and next_population:
                next_population[0] = best_solution[:]
            population = next_population

        return best_solution, best_fitness, best_violations, (time.time() - start) * 1000.0

    def simulated_annealing(self, initial_solution: Optional[ScheduleVector] = None, max_iterations: int = 1200) -> Tuple[ScheduleVector, float, Dict[str, float], float]:
        start = time.time()
        if not self.lessons or not self.auditoriums or not self.time_slots:
            return [], float("inf"), {}, 0.0

        lesson_map = {lesson.id: lesson for lesson in self.lessons}
        aud_map = {aud.id: aud for aud in self.auditoriums}
        slot_map = {slot.id: slot for slot in self.time_slots}

        current = initial_solution[:] if initial_solution else self._create_individual()
        if not current:
            return [], float("inf"), {}, 0.0

        current_fitness, current_violations = self._calculate_fitness(current, lesson_map, aud_map, slot_map)
        best = current[:]
        best_fitness = current_fitness
        best_violations = current_violations

        temperature = 1000.0
        cooling = 0.995

        for _ in range(max_iterations):
            if not current:
                break
            neighbor = current[:]
            mutate_index = random.randrange(len(neighbor))
            lesson_id, _, _, _ = neighbor[mutate_index]
            lesson = lesson_map.get(lesson_id)
            if lesson:
                aud = self._get_auditorium_for_lesson(lesson)
                slot = random.choice(self.time_slots)
                parity = random.choice(["Ч", "НЧ"])
                if aud:
                    neighbor[mutate_index] = (lesson_id, aud.id, slot.id, parity)

            neighbor_fitness, neighbor_viol = self._calculate_fitness(neighbor, lesson_map, aud_map, slot_map)
            delta = neighbor_fitness - current_fitness
            if delta < 0 or random.random() < math.exp(-(delta / max(temperature, 1e-9))):
                current = neighbor
                current_fitness = neighbor_fitness
                current_violations = neighbor_viol

            if current_fitness < best_fitness:
                best = current[:]
                best_fitness = current_fitness
                best_violations = current_violations

            temperature *= cooling
            if temperature < 1:
                break

        return best, best_fitness, best_violations, (time.time() - start) * 1000.0

    def greedy_algorithm(self) -> Tuple[ScheduleVector, float, Dict[str, float], float]:
        start = time.time()
        if not self.lessons or not self.auditoriums or not self.time_slots:
            return [], float("inf"), {}, 0.0

        lesson_map = {lesson.id: lesson for lesson in self.lessons}
        aud_map = {aud.id: aud for aud in self.auditoriums}
        slot_map = {slot.id: slot for slot in self.time_slots}

        schedule: ScheduleVector = []
        used_teacher = set()
        used_group = set()
        used_aud = set()

        sorted_lessons = sorted(self.lessons, key=lambda lesson: (lesson.lesson_type != LessonType.LECTURE, -lesson.student_count, -lesson.hours_per_semester))

        for lesson in sorted_lessons:
            best_choice = None
            best_increment = float("inf")
            candidate_auditoriums = [aud for aud in self.auditoriums if aud.seats >= lesson.student_count]
            if not candidate_auditoriums:
                candidate_auditoriums = self.auditoriums[:]

            for aud in candidate_auditoriums[:30]:
                for slot in self.time_slots:
                    for parity in ["Ч", "НЧ"]:
                        key_teacher = (lesson.teacher, slot.day, slot.pair_number, parity)
                        key_group = (lesson.group, slot.day, slot.pair_number, parity)
                        key_aud = (aud.name, slot.day, slot.pair_number, parity)
                        if key_teacher in used_teacher or key_group in used_group or key_aud in used_aud:
                            continue

                        trial = schedule + [(lesson.id, aud.id, slot.id, parity)]
                        fitness, _ = self._calculate_fitness(trial, lesson_map, aud_map, slot_map)
                        if fitness < best_increment:
                            best_increment = fitness
                            best_choice = (lesson.id, aud.id, slot.id, parity, key_teacher, key_group, key_aud)

            if best_choice:
                lesson_id, aud_id, slot_id, parity, key_teacher, key_group, key_aud = best_choice
                schedule.append((lesson_id, aud_id, slot_id, parity))
                used_teacher.add(key_teacher)
                used_group.add(key_group)
                used_aud.add(key_aud)

        final_fitness, final_violations = self._calculate_fitness(schedule, lesson_map, aud_map, slot_map)
        return schedule, final_fitness, final_violations, (time.time() - start) * 1000.0

    def run_combined_optimization(self) -> Dict:
        results: Dict[str, Dict] = {}

        ga_solution, ga_fitness, ga_violations, ga_time = self.genetic_algorithm()
        results["genetic"] = {
            "solution": ga_solution,
            "fitness": ga_fitness,
            "violations": ga_violations,
            "time_ms": ga_time,
        }

        if ga_solution:
            sa_solution, sa_fitness, sa_violations, sa_time = self.simulated_annealing(initial_solution=ga_solution)
        else:
            sa_solution, sa_fitness, sa_violations, sa_time = [], float("inf"), {}, 0.0

        results["annealing"] = {
            "solution": sa_solution,
            "fitness": sa_fitness,
            "violations": sa_violations,
            "time_ms": sa_time,
        }

        best_algo = "annealing" if sa_fitness < ga_fitness else "genetic"
        best_payload = results[best_algo]

        if not best_payload["solution"]:
            greedy_solution, greedy_fitness, greedy_violations, greedy_time = self.greedy_algorithm()
            results["greedy"] = {
                "solution": greedy_solution,
                "fitness": greedy_fitness,
                "violations": greedy_violations,
                "time_ms": greedy_time,
            }
            best_algo = "greedy"
            best_payload = results["greedy"]

        results["best"] = {
            "algorithm": best_algo,
            "solution": best_payload["solution"],
            "fitness": best_payload["fitness"],
            "violations": best_payload["violations"],
            "time_ms": best_payload["time_ms"],
        }
        return results

