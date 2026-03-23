from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from datetime import timedelta
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    APP_NAME: str = "LMS"
    DEBUG:    bool = True

    # ── JWT ────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY:               str = "changeme"
    JWT_ALGORITHM:                str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS:   int = 30

    # ── Database (individual fields — assembled into URL) ──────────────────
    DB_DRIVER:   str = "sqlite+aiosqlite"
    DB_NAME:     str = "lms.db"

    # Optional explicit override
    DATABASE_URL: Optional[str] = None

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @computed_field
    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"{self.DB_DRIVER}:///{self.DB_NAME}"

    @computed_field
    @property
    def access_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    @computed_field
    @property
    def refresh_token_ttl(self) -> timedelta:
        return timedelta(days=self.JWT_REFRESH_TOKEN_EXPIRE_DAYS)


settings = Settings()