from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from passlib.context import CryptContext
from datetime import datetime
from app.database.base import Base

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id:            Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    username:      Mapped[str]          = mapped_column(String(80),  unique=True, nullable=False, index=True)
    email:         Mapped[str]          = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str]          = mapped_column(String(255), nullable=False)
    first_name:    Mapped[str | None]   = mapped_column(String(80))
    last_name:     Mapped[str | None]   = mapped_column(String(80))
    is_active:     Mapped[bool]         = mapped_column(Boolean, default=True)
    is_verified:   Mapped[bool]         = mapped_column(Boolean, default=False)
    created_at:    Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)
    last_login:    Mapped[datetime | None] = mapped_column(DateTime)

    cars: Mapped[list["Car"]] = relationship(back_populates="owner")

    def set_password(self, plain: str):
        self.password_hash = _pwd_ctx.hash(plain)

    def verify_password(self, plain: str) -> bool:
        return _pwd_ctx.verify(plain, self.password_hash)
