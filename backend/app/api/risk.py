"""Sınıf içi dikkat bayrağı. Yalnızca müdür ve öğretmen okuyabilir."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, get_db_with_context
from backend.app.core.bugun import bugun
from backend.app.models import Attendance, Grade, Student, User, UserRole
from backend.app.services.risk import assess_risk
from backend.app.services.takvim import risk_penceresi

router = APIRouter(tags=["risk"])

_IZINLI = frozenset({UserRole.PRINCIPAL.value, UserRole.TEACHER.value})


class RiskItem(BaseModel):
    student_id: int
    name: str
    class_name: str
    flagged: bool
    grade_average: float | None
    unexcused_absences: int
    grade_rank: str | None
    absence_rank: str
    reason: str


def _rol(user: User) -> str:
    role = user.role
    if isinstance(role, UserRole):
        return role.value
    return str(role).lower()


@router.get("/risk", response_model=list[RiskItem])
def read_risk(
    class_name: str | None = Query(default=None),
    lang: Literal["tr", "en"] = Query(default="tr"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_context),
) -> list[dict]:
    """RLS bağlamı get_db_with_context içindeki set_config yolundan gelir.

    Öğretmen yalnızca kendi sınıfını görür. Gerekçe lang dilindedir. Not ve
    devamsızlık satırları takvim.risk_penceresi(bugün) penceresinden süzülür;
    okul öncesinde liste boştur.
    """
    if _rol(current_user) not in _IZINLI:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem yalnızca müdür ve öğretmen hesaplarına açıktır",
        )

    pencere = risk_penceresi(bugun())
    if pencere is None:
        return []
    baslangic, bitis = pencere

    filtrelenen = class_name.strip() if class_name is not None else ""
    students = db.query(Student)
    if filtrelenen:
        students = students.filter(Student.class_name == filtrelenen)
    student_rows = students.all()
    student_ids = [row.id for row in student_rows]
    if student_ids:
        grade_rows = (
            db.query(Grade)
            .filter(
                Grade.student_id.in_(student_ids),
                Grade.date >= baslangic,
                Grade.date <= bitis,
            )
            .all()
        )
        attendance_rows = (
            db.query(Attendance)
            .filter(
                Attendance.student_id.in_(student_ids),
                Attendance.date >= baslangic,
                Attendance.date <= bitis,
            )
            .all()
        )
    else:
        grade_rows = []
        attendance_rows = []
    return assess_risk(student_rows, grade_rows, attendance_rows, lang=lang)
