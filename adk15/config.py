import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config:
    # -----------------------------
    # Gemini (API Key Mode)
    # -----------------------------
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is required.")

    # -----------------------------
    # GCS Artifact Service
    # -----------------------------
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    BUCKET_NAME = os.getenv("BUCKET_NAME")

    if not GOOGLE_APPLICATION_CREDENTIALS:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is required.")

    if not BUCKET_NAME:
        raise ValueError("BUCKET_NAME is required.")

    # Set credentials for GCS
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

    # -----------------------------
    # PostgreSQL
    # -----------------------------
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

