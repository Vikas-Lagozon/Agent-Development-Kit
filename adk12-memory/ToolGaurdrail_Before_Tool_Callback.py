# ============================================================
# Before Tool Callback Example (Fixed & Production Ready)
# ============================================================

import os
import asyncio
from typing import Optional, Dict, Any
from copy import deepcopy

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
from google.genai import types

from config import config

# ------------------------------------------------------------
# Environment Setup
# ------------------------------------------------------------
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

APP_NAME = "guardrail_app"
USER_ID = "user_1"
SESSION_ID = "session_001"

MODEL_NAME = "gemini-2.5-flash"


# ============================================================
# TOOL FUNCTION
# ============================================================

def get_capital_city(country: str) -> str:
    """Retrieves the capital city of a given country."""
    print(f"\n--- Tool 'get_capital_city' executing with country: {country} ---")

    country_capitals = {
        "united states": "Washington, D.C.",
        "canada": "Ottawa",
        "france": "Paris",
        "germany": "Berlin",
    }

    return country_capitals.get(
        country.lower(),
        f"Capital not found for {country}"
    )


capital_tool = FunctionTool(func=get_capital_city)


# ============================================================
# BEFORE TOOL CALLBACK
# ============================================================

def simple_before_tool_modifier(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext
) -> Optional[Dict]:
    """
    Inspect/modify tool arguments or block execution.
    """

    print(f"\n[Callback] Before tool call")
    print(f"[Callback] Agent: {tool_context.agent_name}")
    print(f"[Callback] Tool: {tool.name}")
    print(f"[Callback] Original args: {args}")

    # Always work on a copy for safety
    modified_args = deepcopy(args)

    # --------------------------------------------------------
    # Rule 1: If country is Canada → Change to France
    # --------------------------------------------------------
    if tool.name == "get_capital_city" and modified_args.get("country", "").lower() == "canada":
        print("[Callback] Detected 'Canada'. Changing to 'France'.")
        modified_args["country"] = "France"

        print(f"[Callback] Modified args: {modified_args}")
        return modified_args  # Return modified args

    # --------------------------------------------------------
    # Rule 2: If country is BLOCK → Skip tool execution
    # --------------------------------------------------------
    if tool.name == "get_capital_city" and modified_args.get("country", "").upper() == "BLOCK":
        print("[Callback] Detected 'BLOCK'. Skipping tool execution.")

        return {
            "result": "Tool execution was blocked by before_tool_callback."
        }

    print("[Callback] Proceeding with original args.")
    return None  # Continue normally


# ============================================================
# AGENT DEFINITION
# ============================================================

my_llm_agent = LlmAgent(
    name="BeforeToolCallbackAgent",
    model=MODEL_NAME,
    instruction=(
        "You are an agent that finds capital cities. "
        "Use the get_capital_city tool."
    ),
    description="Demonstrates before_tool_callback",
    tools=[capital_tool],
    before_tool_callback=simple_before_tool_modifier,
)


# ============================================================
# SETUP (Create Once)
# ============================================================

async def setup():
    session_service = InMemorySessionService()

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    runner = Runner(
        agent=my_llm_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    return runner


# ============================================================
# CALL AGENT
# ============================================================

async def call_agent(runner: Runner, query: str):
    print(f"\nUSER: {query}")

    content = types.Content(
        role="user",
        parts=[types.Part(text=query)]
    )

    events = runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content
    )

    async for event in events:
        if event.is_final_response():
            print("AGENT:", event.content.parts[0].text)


# ============================================================
# MAIN FLOW
# ============================================================

async def main():
    runner = await setup()

    # Normal case
    await call_agent(runner, "What is the capital of Germany?")

    # Canada gets modified → France
    await call_agent(runner, "What is the capital of Canada?")

    # BLOCK skips tool
    await call_agent(runner, "What is the capital of BLOCK?")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
    # await main()
    
