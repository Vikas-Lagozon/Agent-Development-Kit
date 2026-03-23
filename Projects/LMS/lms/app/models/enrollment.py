from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from lms.app.database.base import Base


class Enrollment(Base):
    __tablename__ = "enrollments"

    user_id: int = Column(Integer, ForeignKey("users.id"), primary_key=True)
    course_id: int = Column(Integer, ForeignKey("courses.id"), primary_key=True)

    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course"),)