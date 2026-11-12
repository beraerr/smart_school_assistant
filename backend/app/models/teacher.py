from sqlalchemy import Column, Integer, String

from backend.app.core.database import Base


class Teacher(Base):
    """Öğretmen profili; class_name sorumlu / atanmış sınıf."""

    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<Teacher(name={self.name}, class={self.class_name})>"
