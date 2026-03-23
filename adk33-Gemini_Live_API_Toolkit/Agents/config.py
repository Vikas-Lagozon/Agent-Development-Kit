# config.py

import os
from dotenv import load_dotenv, find_dotenv

# Load .env file
load_dotenv(find_dotenv())

class Config:
    # ── Models ────────────────────────────────────────────────────────────────
    MODEL: str          = os.getenv("MODEL", "gemini-2.5-flash")
    RESEARCH_MODEL: str = os.getenv("RESEARCH_MODEL", "gemini-2.5-pro")

    # Half-cascade model — supports both TEXT and AUDIO response modalities.
    # Switch to "gemini-2.5-flash-native-audio-latest" for native audio (AUDIO only).
    LIVE_MODEL: str = os.getenv("LIVE_MODEL", "gemini-live-2.5-flash")

    # Response modality for the Live API session.
    # "TEXT"  — half-cascade models (gemini-live-2.5-flash, gemini-2.0-flash-live-001)
    # "AUDIO" — required for native-audio models; also supported by half-cascade models
    MODALITY: str = os.getenv("LIVE_MODALITY", "TEXT")

    # ── Gemini / Google AI Studio (API Key Mode) ──────────────────────────────
    # Set GOOGLE_GENAI_USE_VERTEXAI=0 for Gemini Live API (development).
    # Set GOOGLE_GENAI_USE_VERTEXAI=1 for Vertex AI Live API (production).
    GOOGLE_GENAI_API_VERSION: str = os.getenv("GOOGLE_GENAI_API_VERSION", "v1beta")
    GOOGLE_GENAI_USE_VERTEXAI: str = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "0")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is required.")

    # ── GCS Artifact Service ──────────────────────────────────────────────────
    GOOGLE_CSE_ID: str = os.getenv("GOOGLE_CSE_ID", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    BUCKET_NAME: str = os.getenv("BUCKET_NAME", "")

    if not GOOGLE_APPLICATION_CREDENTIALS:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is required.")

    if not BUCKET_NAME:
        raise ValueError("BUCKET_NAME is required.")

    # Set credentials path for GCS client libraries
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

    # ── BigQuery ──────────────────────────────────────────────────────────────
    BQ_PROJECT_ID: str      = os.getenv("BQ_PROJECT_ID", "")
    BQ_DATASET: str         = os.getenv("BQ_DATASET", "")
    SERVICE_ACCOUNT_FILE: str = os.getenv("SERVICE_ACCOUNT_FILE", "")

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    DB_HOST: str     = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: str     = os.getenv("DB_PORT", "5432")
    DB_NAME: str     = os.getenv("DB_NAME", "postgres")
    DB_USER: str     = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_SCHEMA: str   = os.getenv("DB_SCHEMA", "market_intelligence")

    SQLALCHEMY_DATABASE_URI: str = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )


# Singleton config instance — import this everywhere
config = Config()

