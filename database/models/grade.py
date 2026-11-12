from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database.base import Base


class Grade(Base):
    """Exam or coursework score for a student in a subject."""

    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject = Column(String, nullable=False)
    grade = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    student = relationship("Student", back_populates="grades")

    def __repr__(self) -> str:
        return f"<Grade(student_id={self.student_id}, subject={self.subject}, grade={self.grade})>"
