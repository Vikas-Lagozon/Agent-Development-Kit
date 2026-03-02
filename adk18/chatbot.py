# chatbot.py
import os
import asyncio
from google.adk.agents import Agent
from google.adk.sessions import DatabaseSessionService
from google.adk import Runner
import google.genai.types as types
from config import config
import uuid

# -----------------------------
# Constants
# -----------------------------
APP_NAME = "Jarvis"
USER_ID = "user_001"
MODEL = "gemini-2.5-flash"

# -----------------------------
# API Key Setup
# -----------------------------
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# -----------------------------
# System Instruction
# -----------------------------
SYSTEM_INSTRUCTION = """
You are a helpful and professional assistant.
Responsibilities:
- Maintain context from previous messages in the same session.
- Respond concisely, clearly, and politely.
- If you do not know the answer, admit it.
"""

# -----------------------------
# Persistent Agent
# -----------------------------
chat_agent = Agent(
    name="persistent_chat_agent",
    model=MODEL,
    description="A chatbot that stores conversations in Postgres.",
    instruction=SYSTEM_INSTRUCTION,
)

# -----------------------------
# Database Session Service
# -----------------------------
session_service = DatabaseSessionService(
    db_url=config.SQLALCHEMY_DATABASE_URI,
    connect_args={"server_settings": {"search_path": config.DB_SCHEMA}}
)

# -----------------------------
# Runner
# -----------------------------
runner = Runner(
    app_name=APP_NAME,
    agent=chat_agent,
    session_service=session_service
)

# -----------------------------
# Session helpers
# -----------------------------
async def get_or_create_session(user_id: str, session_id: str):
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id
    )
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
    return session

# -----------------------------
# Streaming Chat generator
# -----------------------------
async def chat_stream(user_input: str, session_id: str):
    await get_or_create_session(USER_ID, session_id)

    content = types.Content(
        role="user",
        parts=[types.Part(text=user_input)]
    )

    events = runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content
    )

    async for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    yield part.text

