import os
from dotenv import load_dotenv

# Load .env
load_dotenv()


class Config:
    # -------------------------------------------------
    # Force API Key Mode (NO Vertex AI)
    # -------------------------------------------------
    USE_VERTEX = False  # Hard disable Vertex AI

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is required when not using Vertex AI.")

    # Explicitly remove Vertex credentials if present
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

    # -------------------------------------------------
    # PostgreSQL Configuration
    # -------------------------------------------------
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "postgres")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_SCHEMA = os.getenv("DB_SCHEMA", "market_intelligence")

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )


# Create config instance
config = Config()

