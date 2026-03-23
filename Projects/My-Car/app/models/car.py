from sqlalchemy import Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database.base import Base


class Car(Base):
    __tablename__ = "cars"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    owner_id:    Mapped[int]           = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    make:        Mapped[str]           = mapped_column(String(50), nullable=False)
    model:       Mapped[str]           = mapped_column(String(50), nullable=False)
    year:        Mapped[int]           = mapped_column(Integer, nullable=False)
    price:       Mapped[float]         = mapped_column(Float, nullable=False)
    description: Mapped[str | None]    = mapped_column(String(255))
    is_available:Mapped[bool]          = mapped_column(Boolean, default=True)
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship(back_populates="cars")
