# chatbot.py
# ─────────────────────────────────────────────────────────────
# Jarvis Chatbot Module with MCP Toolsets
# ─────────────────────────────────────────────────────────────

import os
import sys
import logging
import certifi
from datetime import datetime

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
from Agents.ResearchAgent.research import research_agent, get_current_datetime
from Agents.ProblemSolverAgent.problem_solver import problem_solver_agent
from Agents.PythonAgent.python_code import python_agent
from Agents.PlannerAgent.planner import planner_agent

# ── Logging Setup ─────────────────────────────────────────────
LOG_DIR = "log"
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = os.path.join(LOG_DIR, f"log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Log file: {log_filename}")

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

# 1. Expense Tracker MCP
expense_tracker_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk29\MCPServer\expense_tracker_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk29\MCPServer",
        ),
        timeout_in_seconds=30,
    )
)

# 2. To-Do MCP
to_do_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk29\MCPServer\to_do_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk29\MCPServer",
        ),
        timeout_in_seconds=30,
    )
)

# 3. File System MCP
file_system_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk29\MCPServer\FileSystemMCP\file_system_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk29\MCPServer\FileSystemMCP",
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

You have access to the following tools and agents:

1. get_current_datetime
   - Check the current date, time, and day.

2. research_agent
   - Perform deep research and retrieve live web data.

3. expense_tracker tools
   - Record, manage, and retrieve expenses.

4. to_do tools
   - Create, update, delete, and manage tasks.

5. file_system tools
   - Read, write, list, and manage files and folders on the local file system.

6. problem_solver_agent
   - Analyse programming errors, exceptions, stack traces, bugs, and technical issues.
   - Identifies root causes via Google Search and provides step-by-step solutions.

7. python_agent
   - Applies a given solution or set of changes to a provided Python script.
   - Returns the complete updated Python script with all changes applied.

8. planner_agent
   - Creates a complete project from scratch given a project description.
   - Researches best practices, designs full directory structure, generates starter
     code for all files, physically creates the project on disk, and produces
     a detailed PROJECT.md documentation file.


DELEGATION RULES:

1. Date/Time:
   If the user asks for the current time or date, use get_current_datetime.

2. Research:
   Delegate complex research or latest news to research_agent.

3. Expense Tracking:
   Use expense_tracker tools when the user wants to add or check expenses.

4. Task Management:
   Use to_do tools when the user wants to manage tasks or reminders.

5. File System:
   Use file_system tools when the user wants to read, write, list, move,
   or delete files and folders on the local system.

6. Problem Solving — MANDATORY RULE:
   You MUST use transfer_to_agent with agent_name="problem_solver_agent" when
   the user's message contains ANY of the following:
   - An error message or exception (e.g. TypeError, ValueError, ImportError,
     NullPointerException, segmentation fault, etc.)
   - A stack trace or traceback
   - A bug description or unexpected behaviour in code
   - A configuration or environment error
   - A dependency, import, or installation problem
   - Any sentence like "I'm getting an error", "this is not working",
     "how do I fix", "why is this failing", "debug this", "solve this error"
   Do NOT try to answer the problem yourself. ALWAYS transfer to problem_solver_agent.

7. Python Script Modification — MANDATORY RULE:
   You MUST use transfer_to_agent with agent_name="python_agent" when
   the user provides a Python script AND asks you to:
   - Apply a solution, fix, or patch to it
   - Modify, update, refactor, or rewrite it
   - Add, remove, or change specific parts of the code
   - Implement a feature or improvement described in text
   The user message will typically contain a code block (```python ... ```)
   alongside instructions describing what changes to make.
   Do NOT modify the script yourself. ALWAYS transfer to python_agent.

8. Project Planning & Scaffolding — MANDATORY RULE:
   You MUST use transfer_to_agent with agent_name="planner_agent" when
   the user asks to:
   - Create a new project from scratch
   - Scaffold or bootstrap a project
   - Plan a project directory structure
   - Generate a project layout with files and folders
   - Set up a new application, service, API, or tool
   Trigger phrases: "create a project", "build a project", "scaffold",
   "plan a project", "set up a new", "create the structure for",
   "generate project files", "start a new project".
   Do NOT plan or create the project yourself. ALWAYS transfer to planner_agent.


Always:
- Maintain session context
- Provide clear structured answers
- Format responses using markdown
""",
    sub_agents=[
        research_agent,
        problem_solver_agent,
        python_agent,
        planner_agent,
    ],
    tools=[
        get_current_datetime,
        expense_tracker_mcp,
        to_do_mcp,
        file_system_mcp,
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
    problem_solver_agent.name,
    python_agent.name,
    planner_agent.name,
}

# ─────────────────────────────────────────────────────────────
# SESSION HELPER
# ─────────────────────────────────────────────────────────────

async def get_or_create_session(user_id: str, session_id: str):
    logger.info(f"Getting or creating session: user_id={user_id}, session_id={session_id}")

    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    if session is None:
        logger.info(f"Session not found. Creating new session: session_id={session_id}")
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
    else:
        logger.info(f"Existing session found: session_id={session_id}")

    return session

# ─────────────────────────────────────────────────────────────
# STREAMING CHAT FUNCTION
# ─────────────────────────────────────────────────────────────

async def chat_stream(user_input: str, session_id: str):
    logger.info(f"chat_stream called | session_id={session_id} | input={user_input!r}")

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
                logger.info(f"Final response chunk | session_id={session_id} | length={len(part.text)}")
                yield part.text

