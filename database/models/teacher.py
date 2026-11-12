from sqlalchemy import Column, Integer, String

from database.base import Base


class Teacher(Base):
    """Teacher profile; class_name is the homeroom / assigned class."""

    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<Teacher(name={self.name}, class={self.class_name})>"
