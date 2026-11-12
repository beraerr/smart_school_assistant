import enum

from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from database.base import Base


class UserRole(str, enum.Enum):
    """Application roles — aligned with the final system's RBAC (Week 3+)."""

    PRINCIPAL = "principal"
    TEACHER = "teacher"
    PARENT = "parent"
    STUDENT = "student"


class User(Base):
    """Login account linked to a role and optional domain entity via related_id."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    related_id = Column(Integer, nullable=True)  # student_id for parent/student, teacher_id for teacher
    related_class = Column(String, nullable=True)  # class name for teacher

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
