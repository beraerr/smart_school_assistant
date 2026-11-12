"""
Mevcut veritabanını database/mock_data.json dosyasına dondurur.

students, teachers, grades ve attendance satırları olduğu gibi yazılır.
users için parola hash'i yazılmaz; bilinen demo parolası düz metin konur.
Tarihler mutlak YYYY-MM-DD değeridir. Veritabanına yazmaz.

Proje kökünden:
    python database/export_mock_data.py
"""

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.models import Attendance, Grade, Student, Teacher, User, UserRole

_MOCK_DATA_PATH = Path(__file__).resolve().with_name("mock_data.json")

# Seed sırasında hash'lenir. Burada düz metin durur; hash dışarı çıkmaz.
_MOCK_PASSWORDS = {
    "principal": "admin123",
    "teacher1": "teacher123",
    "teacher2": "teacher123",
    "parent1": "parent123",
    "parent2": "parent123",
    "student1": "student123",
    "student2": "student123",
}


def _role_value(role: UserRole | str) -> str:
    if isinstance(role, UserRole):
        return role.value
    try:
        return UserRole[str(role)].value
    except KeyError:
        return UserRole(str(role)).value


def export_mock_data(db: Session, path: Path = _MOCK_DATA_PATH) -> None:
    """Açık oturumdaki satırları mock_data.json olarak yazar."""
    teachers = [
        {"id": row.id, "name": row.name, "class_name": row.class_name}
        for row in db.query(Teacher).order_by(Teacher.id)
    ]
    students = [
        {
            "id": row.id,
            "name": row.name,
            "class_name": row.class_name,
            "parent_id": row.parent_id,
        }
        for row in db.query(Student).order_by(Student.id)
    ]
    users = []
    for row in db.query(User).order_by(User.id):
        password = _MOCK_PASSWORDS.get(row.username)
        if password is None:
            raise SystemExit(f"Bilinen mock parola yok: {row.username}")
        users.append(
            {
                "id": row.id,
                "username": row.username,
                "password": password,
                "role": _role_value(row.role),
                "related_id": row.related_id,
                "related_class": row.related_class,
            }
        )
    grades = [
        {
            "id": row.id,
            "student_id": row.student_id,
            "subject": row.subject,
            "grade": row.grade,
            "date": row.date.isoformat(),
        }
        for row in db.query(Grade).order_by(Grade.id)
    ]
    attendance = [
        {
            "id": row.id,
            "student_id": row.student_id,
            "date": row.date.isoformat(),
            "status": row.status,
        }
        for row in db.query(Attendance).order_by(Attendance.id)
    ]

    payload = {
        "teachers": teachers,
        "students": students,
        "users": users,
        "grades": grades,
        "attendance": attendance,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if "$2" in text:
        raise SystemExit("mock_data.json parola hash'i içeremez")
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")
    print(f"  Teachers:   {len(teachers)}")
    print(f"  Students:   {len(students)}")
    print(f"  Users:      {len(users)}")
    print(f"  Grades:     {len(grades)}")
    print(f"  Attendance: {len(attendance)}")


def main() -> None:
    db = SessionLocal()
    try:
        export_mock_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
