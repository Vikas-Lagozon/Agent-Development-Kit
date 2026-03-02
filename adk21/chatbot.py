# chatbot.py
# ─────────────────────────────────────────────────────────────
# Jarvis Chatbot Module using LlmAgent
# ─────────────────────────────────────────────────────────────

import os
import logging
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.sessions import DatabaseSessionService
from google.adk import Runner
import google.genai.types as types
from config import config

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Import sub-agents and shared tools ────────────────────────
# We import both the agent and the function from research.py
from research import research_agent, get_current_datetime

# ── Constants ─────────────────────────────────────────────────
APP_NAME = "Jarvis"
USER_ID = "user_001"
MODEL    = config.MODEL

# ── Environment ───────────────────────────────────────────────
if config.GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# ── Root / Orchestrator Agent ─────────────────────────────────
root_agent = LlmAgent(
    name="jarvis_root_agent",
    model=MODEL,
    instruction="""
You are Jarvis, a highly capable and professional AI assistant.

You have access to the following:
  - `get_current_datetime`: A tool to check the current date, time, and day.
  - `research_agent`: A specialist for deep research and live web data.

DELEGATION & TOOL RULES:

1. **Date/Time**: If the user asks "What time is it?" or "What day is today?", use the `get_current_datetime` tool directly. Do NOT delegate this to the research agent.
2. **Research**: Delegate to `research_agent` for:
  • Current events, news, or latest developments.
  • Statistics, financial data, or product releases.
  • Complex topics requiring a deep report.
3. **Direct Response**: Answer directly for coding, math, general logic, or casual conversation.

Always:
  - Maintain session context.
  - Be clear, structured, and professional.
  - Format using markdown.
""",
    sub_agents=[research_agent],
    tools=[get_current_datetime], # Register the tool here
)

# ── App ───────────────────────────────────────────────────────
jarvis_app = App(
    name="jarvis",
    root_agent=root_agent,
)

# ── Database Session Service ──────────────────────────────────
session_service = DatabaseSessionService(
    db_url=config.SQLALCHEMY_DATABASE_URI,
    connect_args={
        "server_settings": {
            "search_path": config.DB_SCHEMA
        }
    }
)

# ── Runner ────────────────────────────────────────────────────
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)

# ── Known agent names (for streaming clarity) ─────────────────
ALL_AGENT_NAMES = {
    root_agent.name,
    research_agent.name,
}

# ── Session Helper ────────────────────────────────────────────
async def get_or_create_session(user_id: str, session_id: str):
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
    return session

# ── Streaming Chat Generator ──────────────────────────────────
async def chat_stream(user_input: str, session_id: str):
    await get_or_create_session(USER_ID, session_id)

    content = types.Content(
        role="user",
        parts=[types.Part(text=user_input)],
    )

    events = runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    )

    async for event in events:
        if not getattr(event, "content", None) or not event.content.parts:
            continue

        if not event.is_final_response():
            continue

        for part in event.content.parts:
            if getattr(part, "text", None):
                yield part.text