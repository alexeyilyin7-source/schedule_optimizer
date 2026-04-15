from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class LessonType(str, Enum):
    LECTURE = "Лекции"
    PRACTICE = "Практ. занятия"
    LAB = "Лаб. занятия"

class Lesson(BaseModel):
    id: int
    discipline: str
    institute: str
    direction: str
    program: str
    course: int
    group: str
    group_count: int
    student_count: int
    teacher: str
    lesson_type: LessonType
    hours_per_semester: int
    note: Optional[str] = ""

class Auditorium(BaseModel):
    id: int
    name: str
    category: str
    seats: int
    building: str
    floor: Optional[int] = None
    comment: Optional[str] = ""

class TimeSlot(BaseModel):
    id: int
    day: str
    start_time: str
    end_time: str
    pair_number: int

class ScheduleEntry(BaseModel):
    lesson_id: int
    group: str
    discipline: str
    teacher: str
    lesson_type: LessonType
    auditorium: str
    day: str
    pair_number: int
    week_parity: str

class OptimizationResult(BaseModel):
    schedule: List[ScheduleEntry]
    fitness_score: float
    algorithm_used: str
    violations: Dict[str, int]
    execution_time_ms: int