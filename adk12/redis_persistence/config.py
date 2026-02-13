import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_GENAI_USE_VERTEXAI = "0"  # Explicitly disable Vertex AI

    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_PASSWORD = "myredispassword"
    REDIS_TTL = 3600


config = Config()
