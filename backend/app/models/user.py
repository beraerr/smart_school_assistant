import enum

from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class UserRole(str, enum.Enum):
    """Uygulama rolleri — final sistemdeki RBAC ile uyumlu (Hafta 3+)."""

    PRINCIPAL = "principal"
    TEACHER = "teacher"
    PARENT = "parent"
    STUDENT = "student"


class User(Base):
    """Giriş hesabı; role ve isteğe bağlı related_id ile domain kaydına bağlanır."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    related_id = Column(Integer, nullable=True)  # parent/student için student_id, teacher için teacher_id
    related_class = Column(String, nullable=True)  # öğretmen için sınıf adı

    student = relationship(
        "Student",
        foreign_keys="Student.id",
        uselist=False,
        primaryjoin="and_(User.related_id==Student.id, User.role=='student')",
    )
    teacher = relationship(
        "Teacher",
        foreign_keys="Teacher.id",
        uselist=False,
        primaryjoin="and_(User.related_id==Teacher.id, User.role=='teacher')",
    )

    def __repr__(self) -> str:
        return f"<User(username={self.username}, role={self.role})>"
