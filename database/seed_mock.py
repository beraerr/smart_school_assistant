"""
Yerel demo için mock okul verisi ekler.

Parolalar passlib bcrypt ile hash'lenerek users.password_hash alanına yazılır.

Proje kökünden (init_db.py sonrası):
    python database/seed_mock.py
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models import Attendance, Grade, Student, Teacher, User, UserRole


def _clear_tables(db: Session) -> None:
    """Tabloları boşaltır; betik yeniden çalıştırılınca aynı kimlikler üretilsin.

    PostgreSQL DELETE kimlik dizisini geri sarmadığı için TRUNCATE kullanılır.
    Demo girişleri ve RLS testleri ilk öğrencinin id değerinin 1 kalmasını bekler.
    """
    db.execute(
        text(
            "TRUNCATE TABLE attendance, grades, students, teachers, users "
            "RESTART IDENTITY CASCADE"
        )
    )
    db.commit()


def seed_mock_data(db: Session) -> None:
    teacher1 = Teacher(name="Ahmet Öğretmen", class_name="9-A")
    teacher2 = Teacher(name="Ayşe Öğretmen", class_name="10-B")
    db.add_all([teacher1, teacher2])
    db.flush()

    students_data = [
        {"name": "Ali Yılmaz", "class_name": "9-A", "total_absences": 3},
        {"name": "Zeynep Demir", "class_name": "9-A", "total_absences": 7},
        {"name": "Mehmet Kaya", "class_name": "9-A", "total_absences": 2},
        {"name": "Elif Şahin", "class_name": "10-B", "total_absences": 1},
        {"name": "Can Arslan", "class_name": "10-B", "total_absences": 6},
        {"name": "Selin Yıldız", "class_name": "10-B", "total_absences": 4},
        {"name": "Deniz Aktaş", "class_name": "5-A", "total_absences": 0},
        {"name": "Ece Polat", "class_name": "5-A", "total_absences": 2},
        {"name": "Burak Çelik", "class_name": "5-A", "total_absences": 5},
        {"name": "Mira Koç", "class_name": "5-A", "total_absences": 1},
        {"name": "Kerem Güneş", "class_name": "9-A", "total_absences": 8},
        {"name": "Lina Öztürk", "class_name": "10-B", "total_absences": 3},
    ]

    students: list[Student] = []
    for row in students_data:
        student = Student(**row)
        db.add(student)
        students.append(student)
    db.flush()

    principal_user = User(
        username="principal",
        password_hash=get_password_hash("admin123"),
        role=UserRole.PRINCIPAL,
        related_id=None,
        related_class=None,
    )
    teacher1_user = User(
        username="teacher1",
        password_hash=get_password_hash("teacher123"),
        role=UserRole.TEACHER,
        related_id=teacher1.id,
        related_class="9-A",
    )
    teacher2_user = User(
        username="teacher2",
        password_hash=get_password_hash("teacher123"),
        role=UserRole.TEACHER,
        related_id=teacher2.id,
        related_class="10-B",
    )
    parent1_user = User(
        username="parent1",
        password_hash=get_password_hash("parent123"),
        role=UserRole.PARENT,
        related_id=students[0].id,
        related_class=None,
    )
    parent2_user = User(
        username="parent2",
        password_hash=get_password_hash("parent123"),
        role=UserRole.PARENT,
        related_id=students[1].id,
        related_class=None,
    )
    student1_user = User(
        username="student1",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        related_id=students[0].id,
        related_class=None,
    )
    student2_user = User(
        username="student2",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        related_id=students[1].id,
        related_class=None,
    )
    db.add_all(
        [
            principal_user,
            teacher1_user,
            teacher2_user,
            parent1_user,
            parent2_user,
            student1_user,
            student2_user,
        ]
    )
    db.flush()

    students[0].parent_id = parent1_user.id
    students[1].parent_id = parent2_user.id

    subjects = ["Matematik", "Fizik", "Kimya", "Türkçe", "Tarih"]
    today = date.today()

    for student in students:
        for subject in subjects:
            for month_offset in range(3):
                grade_date = today - timedelta(days=30 * month_offset)
                db.add(
                    Grade(
                        student_id=student.id,
                        subject=subject,
                        grade=round(random.uniform(50, 100), 2),
                        date=grade_date,
                    )
                )

    for day_offset in range(30):
        attendance_date = today - timedelta(days=day_offset)
        for student in students:
            status = random.choice(
                ["present", "present", "present", "present", "absent", "excused"]
            )
            db.add(
                Attendance(
                    student_id=student.id,
                    date=attendance_date,
                    status=status,
                )
            )

    db.commit()

    print("Mock data inserted successfully.")
    print(f"  Teachers: {db.query(Teacher).count()}")
    print(f"  Students: {db.query(Student).count()}")
    print(f"  Users:    {db.query(User).count()} (all four roles represented)")
    print("\nDemo logins (parolalar veritabanında bcrypt hash):")
    print("  Principal: principal / admin123")
    print("  Teacher 1: teacher1 / teacher123 (9-A)")
    print("  Teacher 2: teacher2 / teacher123 (10-B)")
    print("  Parent 1:  parent1 / parent123 (Ali Yılmaz)")
    print("  Parent 2:  parent2 / parent123 (Zeynep Demir)")
    print("  Student 1: student1 / student123 (Ali Yılmaz)")
    print("  Student 2: student2 / student123 (Zeynep Demir)")


def main() -> None:
    db = SessionLocal()
    try:
        _clear_tables(db)
        seed_mock_data(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
