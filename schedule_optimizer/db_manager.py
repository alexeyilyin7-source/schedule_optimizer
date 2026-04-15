from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import json
from typing import List, Dict

# Исправлено: используем правильный импорт declarative_base
Base = declarative_base()


class Institute(Base):
    __tablename__ = 'institutes'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    abbreviation = Column(String(9), nullable=False)


class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True)
    institute_id = Column(Integer, ForeignKey('institutes.id'))
    name = Column(String(255), nullable=False)
    head_name = Column(String(255))


class Teacher(Base):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey('departments.id'))
    institute_id = Column(Integer, ForeignKey('institutes.id'))
    full_name = Column(String(255), nullable=False)
    email = Column(String(100), nullable=False)
    max_hours_per_day = Column(Integer, default=6)
    phone = Column(String(16))
    preferences = Column(Text)


class StudentGroup(Base):
    __tablename__ = 'student_groups'
    id = Column(Integer, primary_key=True)
    institute_id = Column(Integer, ForeignKey('institutes.id'))
    department_id = Column(Integer, ForeignKey('departments.id'))
    code = Column(String(50), nullable=False)
    course = Column(Integer, nullable=False)
    level = Column(String(20))
    student_count = Column(Integer)


class Discipline(Base):
    __tablename__ = 'disciplines'
    id = Column(Integer, primary_key=True)
    code = Column(String(45), nullable=False)
    name = Column(String(45), nullable=False)
    lesson_type = Column(String(10))


class Curriculum(Base):
    __tablename__ = 'curriculum'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('student_groups.id'))
    discipline_id = Column(Integer, ForeignKey('disciplines.id'))
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    total_hours = Column(Integer)
    semester = Column(String(20))
    even_weeks = Column(Integer, default=1)
    odd_weeks = Column(Integer, default=1)


class Auditorium(Base):
    __tablename__ = 'auditoriums'
    id = Column(Integer, primary_key=True)
    number = Column(String(45), nullable=False)
    building = Column(String(45))
    capacity = Column(Integer)
    type = Column(String(20))
    equipment = Column(Text)


class TimeSlot(Base):
    __tablename__ = 'time_slots'
    id = Column(Integer, primary_key=True)
    day = Column(String(2))
    start_time = Column(String(8))
    end_time = Column(String(8))
    pair_number = Column(Integer)


class ScheduleRecord(Base):
    __tablename__ = 'schedule_records'
    id = Column(Integer, primary_key=True)
    curriculum_id = Column(Integer, ForeignKey('curriculum.id'))
    auditorium_id = Column(Integer, ForeignKey('auditoriums.id'))
    time_slot_id = Column(Integer, ForeignKey('time_slots.id'))
    discipline_id = Column(Integer, ForeignKey('disciplines.id'))
    week_parity = Column(String(2))
    created_at = Column(String(50))
    is_cancelled = Column(Integer, default=0)
    cancel_reason = Column(Text)


class ScheduleDB:
    def __init__(self, db_path="schedule.db"):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_schedule(self, schedule_records: List[Dict]):
        """Сохранение расписания в БД"""
        session = self.Session()
        try:
            for record in schedule_records:
                db_record = ScheduleRecord(**record)
                session.add(db_record)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_schedule(self, group_code: str = None, teacher_name: str = None):
        """Получение расписания из БД"""
        session = self.Session()
        try:
            query = session.query(ScheduleRecord)
            results = query.all()
            return results
        finally:
            session.close()


if __name__ == "__main__":
    # Тестирование БД
    db = ScheduleDB("test_schedule.db")
    print("✅ База данных успешно создана")