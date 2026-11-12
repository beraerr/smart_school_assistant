from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database.base import Base


class Student(Base):
    """Student profile; parent_id points at the parent user's row in users."""

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)  # e.g., "9-A", "10-B"
    total_absences = Column(Integer, default=0)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship(
        "Attendance", back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Student(name={self.name}, class={self.class_name})>"
