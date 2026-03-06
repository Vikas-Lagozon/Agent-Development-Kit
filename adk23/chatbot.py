# chatbot.py
# ─────────────────────────────────────────────────────────────
# Jarvis Chatbot Module with MCP Toolsets
# ─────────────────────────────────────────────────────────────

import os
import sys
import logging
import certifi

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.sessions import DatabaseSessionService
from google.adk import Runner

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

import google.genai.types as types

from config import config

# Import sub-agent + tool
from research import research_agent, get_current_datetime

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────
APP_NAME = "Jarvis"
USER_ID = "user_001"
MODEL = config.MODEL

# ── Environment Setup ─────────────────────────────────────────
if config.GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# SSL Fix
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

PATH_TO_PYTHON = sys.executable

# ─────────────────────────────────────────────────────────────
# MCP TOOLSETS
# ─────────────────────────────────────────────────────────────

# 1️⃣ Web Reader MCP
web_reader_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk22\MCPServer\my_adk_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk22\MCPServer",
        ),
        timeout_in_seconds=30,
    )
)

# 2️⃣ Expense Tracker MCP
expense_tracker_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk22\MCPServer\expense_tracker_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk22\MCPServer",
        ),
        timeout_in_seconds=30,
    )
)

# 3️⃣ To-Do MCP
to_do_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk22\MCPServer\to_do_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk22\MCPServer",
        ),
        timeout_in_seconds=30,
    )
)

# ─────────────────────────────────────────────────────────────
# ROOT / ORCHESTRATOR AGENT
# ─────────────────────────────────────────────────────────────

root_agent = LlmAgent(
    name="jarvis_root_agent",
    model=MODEL,
    instruction="""
You are Jarvis, a highly capable and professional AI assistant.

You have access to the following tools:

1. get_current_datetime
   - Check the current date, time, and day.

2. research_agent
   - Perform deep research and retrieve live web data.

3. web_reader tools
   - Browse and extract information from websites.

4. expense_tracker tools
   - Record, manage, and retrieve expenses.

5. to_do tools
   - Create, update, delete, and manage tasks.

DELEGATION RULES:

1. Date/Time:
   If the user asks for the current time or date, use get_current_datetime.

2. Research:
   Delegate complex research or latest news to research_agent.

3. Web Browsing:
   Use web_reader tools when specific webpages need to be analyzed.

4. Expense Tracking:
   Use expense_tracker tools when the user wants to add or check expenses.

5. Task Management:
   Use to_do tools when the user wants to manage tasks or reminders.

Always:
- Maintain session context
- Provide clear structured answers
- Format responses using markdown
""",
    sub_agents=[research_agent],
    tools=[
        get_current_datetime,
        web_reader_mcp,
        expense_tracker_mcp,
        to_do_mcp,
    ],
)

# ─────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────

jarvis_app = App(
    name="jarvis",
    root_agent=root_agent,
)

# ─────────────────────────────────────────────────────────────
# DATABASE SESSION SERVICE
# ─────────────────────────────────────────────────────────────

session_service = DatabaseSessionService(
    db_url=config.SQLALCHEMY_DATABASE_URI,
    connect_args={
        "server_settings": {
            "search_path": config.DB_SCHEMA
        }
    },
)

# ─────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────

runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)

# ─────────────────────────────────────────────────────────────
# KNOWN AGENT NAMES
# ─────────────────────────────────────────────────────────────

ALL_AGENT_NAMES = {
    root_agent.name,
    research_agent.name,
}

# ─────────────────────────────────────────────────────────────
# SESSION HELPER
# ─────────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────────
# STREAMING CHAT FUNCTION
# ─────────────────────────────────────────────────────────────

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
