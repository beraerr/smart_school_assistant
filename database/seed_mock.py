"""
Yerel demo için mock okul verisini database/mock_data.json dosyasından yükler.

Parolalar dosyada düz metindir; passlib bcrypt ile hash'lenerek
users.password_hash alanına yazılır. Tarihler dosyadaki mutlak
YYYY-MM-DD değerleridir. total_absences, attendance kayıtlarında
'present' dışı satır sayısı olarak hesaplanır.

Proje kökünden (init_db.py sonrası):
    python database/seed_mock.py
"""

import json
import sys
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.core.security import pwd_context
from backend.app.models import Attendance, Grade, Student, Teacher, User, UserRole

_MOCK_DATA_PATH = Path(__file__).resolve().with_name("mock_data.json")

# Düz parola mock_data.json'da. Tuz kullanıcı adına sabittir; böylece aynı
# parola her seed'de aynı hash'i üretir ve dondurulmuş users satırları değişmez.
_PASSWORD_SALT = {
    "principal": "G2C532oqszPulMpw7hrd0O",
    "teacher1": "cfBKPvvS.gI8tZbe3m0IFu",
    "teacher2": "/MzFPWyu4V/mLNxLnMXxx.",
    "parent1": "Sf4arADpGf68QlF5YqbTa.",
    "parent2": "YSNP2chiw0Zy7p4rHlW0C.",
    "student1": "DKA7ov3Q9PwxtOrpiHLWSu",
    "student2": "h3qqSVnDCC3KyR1JLnqgde",
}


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


def _load_mock_data(path: Path = _MOCK_DATA_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _hash_password(username: str, password: str) -> str:
    salt = _PASSWORD_SALT.get(username)
    if salt is None:
        raise ValueError(f"Sabit bcrypt tuzu yok: {username}")
    return pwd_context.hash(password, salt=salt)


def _add_with_expected_id(db: Session, obj, expected_id: int):
    db.add(obj)
    db.flush()
    if obj.id != expected_id:
        raise RuntimeError(
            f"{type(obj).__tablename__} id {obj.id}, beklenen {expected_id}"
        )
    return obj


def seed_mock_data(db: Session) -> None:
    data = _load_mock_data()

    for row in sorted(data["teachers"], key=lambda item: item["id"]):
        _add_with_expected_id(
            db,
            Teacher(name=row["name"], class_name=row["class_name"]),
            row["id"],
        )

    students: dict[int, Student] = {}
    for row in sorted(data["students"], key=lambda item: item["id"]):
        student = _add_with_expected_id(
            db,
            Student(name=row["name"], class_name=row["class_name"]),
            row["id"],
        )
        students[row["id"]] = student

    for row in sorted(data["users"], key=lambda item: item["id"]):
        _add_with_expected_id(
            db,
            User(
                username=row["username"],
                password_hash=_hash_password(row["username"], row["password"]),
                role=UserRole(row["role"]),
                related_id=row["related_id"],
                related_class=row["related_class"],
            ),
            row["id"],
        )

    for row in data["students"]:
        if row["parent_id"] is not None:
            students[row["id"]].parent_id = row["parent_id"]
    db.flush()

    for row in sorted(data["grades"], key=lambda item: item["id"]):
        _add_with_expected_id(
            db,
            Grade(
                student_id=row["student_id"],
                subject=row["subject"],
                grade=row["grade"],
                date=date.fromisoformat(row["date"]),
            ),
            row["id"],
        )

    for row in sorted(data["attendance"], key=lambda item: item["id"]):
        _add_with_expected_id(
            db,
            Attendance(
                student_id=row["student_id"],
                date=date.fromisoformat(row["date"]),
                status=row["status"],
            ),
            row["id"],
        )

    db.flush()
    for student in students.values():
        student.total_absences = (
            db.query(Attendance)
            .filter(
                Attendance.student_id == student.id,
                Attendance.status != "present",
            )
            .count()
        )

    db.commit()

    print("Mock data inserted successfully.")
    print(f"  Teachers: {db.query(Teacher).count()}")
    print(f"  Students: {db.query(Student).count()}")
    print(f"  Users:    {db.query(User).count()} (all four roles represented)")
    print("\nDemo logins (parolalar veritabanında bcrypt hash):")
    for row in sorted(data["users"], key=lambda item: item["id"]):
        note = ""
        if row["role"] == "teacher" and row["related_class"]:
            note = f" ({row['related_class']})"
        elif row["role"] in {"parent", "student"} and row["related_id"] in students:
            note = f" ({students[row['related_id']].name})"
        label = row["role"].capitalize()
        print(f"  {label}: {row['username']} / {row['password']}{note}")


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
