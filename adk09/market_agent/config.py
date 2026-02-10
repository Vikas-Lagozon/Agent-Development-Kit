# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# ---- Database connection config ----

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "abcd1234")
DB_SCHEMA = os.getenv("DB_SCHEMA", "market_intelligence")

