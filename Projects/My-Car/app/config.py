from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from datetime import timedelta
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    APP_NAME: str = "Car Selling and Buying Website"
    DEBUG:    bool = False

    # ── JWT ────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY:               str = "changeme"
    JWT_ALGORITHM:                str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS:   int = 30

    # ── SQLite ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @computed_field
    @property
    def access_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    @computed_field
    @property
    def refresh_token_ttl(self) -> timedelta:
        return timedelta(days=self.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    @computed_field
    @property
    def alembic_db_url(self) -> str:
        return self.DATABASE_URL


settings = Settings()
