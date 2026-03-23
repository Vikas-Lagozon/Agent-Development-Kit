from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from lms.app.database.base import Base


class Course(Base):
    __tablename__ = "courses"

    id:          Mapped[int]        = mapped_column(Integer, primary_key=True, index=True)
    name:        Mapped[str]        = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active:   Mapped[bool]       = mapped_column(Boolean, default=True)
    created_at:  Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(
        secondary="enrollments", back_populates="courses", lazy="selectin"
    )