"""
agent.py — Agent setup, session management, HITL callback, and runner logic.
"""

import os
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
import google.genai.types as types

from config import config

# -----------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------
APP_NAME  = "PrivacyGuardApp"
USER_ID   = "default_user"
MODEL     = config.MODEL

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

# -----------------------------------------------------------------------
# IN-MEMORY PENDING ACTIONS STORE  (keyed by session_id)
# -----------------------------------------------------------------------
pending_actions: Dict[str, Any] = {}

# -----------------------------------------------------------------------
# TOOL DEFINITION
# -----------------------------------------------------------------------
def sensitive_data_update(record_id: str, new_value: str) -> dict:
    """Updates a record in the database.

    Args:
        record_id: The unique identifier of the record to update.
        new_value: The new value to write into the record.

    Returns:
        A dict describing the outcome of the update.
    """
    return {
        "status": "success",
        "message": f"✅ Record '{record_id}' successfully updated to '{new_value}'",
    }

# -----------------------------------------------------------------------
# HITL CALLBACK — intercepts every tool call before execution
# -----------------------------------------------------------------------
def before_tool_callback(tool, args: dict, tool_context) -> Optional[dict]:
    """
    Called just before ADK executes any tool.
    - Returns a dict  →  ADK skips the real tool and uses this as the result.
    - Returns None    →  ADK runs the real tool normally.
    """
    try:
        session_id = tool_context.invocation_context.session.id
    except AttributeError:
        session_id = tool_context._invocation_context.session.id

    # Park the tool call so the API can ask the human
    pending_actions[session_id] = {
        "tool_name": tool.name,
        "arguments": args,
    }

    # Placeholder result the agent sees while waiting for approval
    return {
        "status": "PENDING_APPROVAL",
        "message": (
            f"Tool '{tool.name}' has been intercepted and requires "
            "human approval before it can be executed."
        ),
    }

# -----------------------------------------------------------------------
# AGENT
# -----------------------------------------------------------------------
root_agent = LlmAgent(
    model=MODEL,
    name="PrivacyAgent",
    instruction="""
    You are a records manager. When a user asks to update data,
    always use the sensitive_data_update tool. Extract record_id and
    new_value from the user request.
    If a tool call returns a PENDING_APPROVAL status, inform the user that
    the action is awaiting human approval via the /approve endpoint.
    """,
    tools=[sensitive_data_update],
    before_tool_callback=before_tool_callback,
)

# -----------------------------------------------------------------------
# SERVICES & RUNNER
# -----------------------------------------------------------------------
session_service  = InMemorySessionService()
artifact_service = InMemoryArtifactService()

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
    artifact_service=artifact_service,
)

# -----------------------------------------------------------------------
# HELPER — guarantee a session exists before using the runner
# -----------------------------------------------------------------------
async def ensure_session(session_id: str) -> None:
    """Create the ADK session the first time we see a session_id."""
    existing = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    if not existing:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )

# -----------------------------------------------------------------------
# HELPER — send one message, collect the final text response
# -----------------------------------------------------------------------
async def run_agent_turn(session_id: str, text: str) -> str:
    """
    run_async() returns an async generator of Event objects.
    We iterate until is_final_response() is True and return that text.
    """
    message = types.Content(
        role="user",
        parts=[types.Part(text=text)],
    )

    final_response = "Agent did not produce a final response."

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text or final_response
            break

    return final_response
