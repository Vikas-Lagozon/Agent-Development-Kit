# chatbot.py
import os
import logging
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.adk.sessions import DatabaseSessionService
from google.adk import Runner
import google.genai.types as types
from config import config

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Import sub-agents ─────────────────────────────────────────
from research import research_agent   # Uses Gemini built-in search grounding

# ── Constants ─────────────────────────────────────────────────
APP_NAME = "Jarvis"
USER_ID  = "user_001"
MODEL    = config.MODEL

# ── Environment ───────────────────────────────────────────────
if config.GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# ── Root / Orchestrator Agent ─────────────────────────────────
root_agent = Agent(
    name="jarvis_root_agent",
    model=MODEL,
    description="Main Jarvis assistant that orchestrates specialist sub-agents.",
    instruction="""
You are Jarvis, a highly capable and professional AI assistant.

You have access to the following specialist sub-agents:
  - `deep_topic_research_agent`: for deep research, current events, and live data.

DELEGATION RULES:

Delegate to `deep_topic_research_agent` when the query involves:
  • Current events, breaking news, recent developments
  • Latest statistics, rankings, scores, financial data
  • Recently released products, tools, papers, updates
  • Any fact that may have changed recently

Answer directly (without delegation) for:
  • Coding and debugging
  • Algorithms and system design
  • Math and logical reasoning
  • Creative writing and brainstorming
  • Stable general knowledge
  • Conversational replies

Always:
  - Maintain session context.
  - Be clear, structured, and professional.
  - Format using markdown.
  - Prefer answering directly if research is not clearly required.
""",
    sub_agents=[research_agent],
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
    """
    Streams only the final user-facing response.

    Handles delegation automatically:
      root_agent → sub-agent → final response
    """

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

        # Skip empty events
        if not getattr(event, "content", None):
            continue

        if not event.content.parts:
            continue

        # Only stream final response chunks
        if not event.is_final_response():
            continue

        for part in event.content.parts:
            if getattr(part, "text", None):
                logger.debug(
                    "Streaming from agent='%s': %d chars",
                    event.author,
                    len(part.text),
                )
                yield part.text
