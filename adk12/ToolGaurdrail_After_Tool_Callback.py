# ============================================================
# After Tool Callback Example (Fixed & Production Ready)
# ============================================================

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
import os
from config import config
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
APP_NAME = "guardrail_app"
USER_ID = "user_1"
SESSION_ID = "session_001"

MODEL_NAME = "gemini-2.5-flash"


# ============================================================
# TOOL FUNCTION
# ============================================================

def get_capital_city(country: str) -> Dict[str, str]:
    """Retrieves the capital city of a given country."""
    print(f"\n--- Tool 'get_capital_city' executing with country: {country} ---")

    country_capitals = {
        "united states": "Washington, D.C.",
        "canada": "Ottawa",
        "france": "Paris",
        "germany": "Berlin",
    }

    return {
        "result": country_capitals.get(
            country.lower(),
            f"Capital not found for {country}"
        )
    }


# Wrap function as ADK tool
capital_tool = FunctionTool(func=get_capital_city)


# ============================================================
# AFTER TOOL CALLBACK
# ============================================================

def simple_after_tool_modifier(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext,
    tool_response: Dict
) -> Optional[Dict]:
    """
    Inspect/modify tool result after execution.
    """

    agent_name = tool_context.agent_name
    tool_name = tool.name

    print(f"\n[Callback] After tool call")
    print(f"[Callback] Agent: {agent_name}")
    print(f"[Callback] Tool: {tool_name}")
    print(f"[Callback] Args: {args}")
    print(f"[Callback] Original tool_response: {tool_response}")

    original_result_value = tool_response.get("result", "")

    # --------------------------------------------------------
    # Example Modification Rule
    # --------------------------------------------------------
    if tool_name == "get_capital_city" and original_result_value == "Washington, D.C.":
        print("[Callback] Modifying tool response for USA")

        modified_response = deepcopy(tool_response)

        modified_response["result"] = (
            f"{original_result_value} "
            "(Note: This is the capital of the USA)."
        )

        modified_response["note_added_by_callback"] = True

        print(f"[Callback] Modified tool_response: {modified_response}")

        return modified_response

    print("[Callback] Passing original response through")
    return None


# ============================================================
# AGENT DEFINITION
# ============================================================

my_llm_agent = LlmAgent(
    name="AfterToolCallbackAgent",
    model=MODEL_NAME,
    instruction=(
        "You are an agent that finds capital cities "
        "using the get_capital_city tool. "
        "Report the result clearly."
    ),
    description="Demonstrates after_tool_callback",
    tools=[capital_tool],
    after_tool_callback=simple_after_tool_modifier,
)


# ============================================================
# SETUP (Create Session Once)
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

    # Turn 1
    await call_agent(runner, "What is the capital of United States?")

    # Turn 2
    await call_agent(runner, "What is the capital of Canada?")

    # Turn 3
    await call_agent(runner, "What is the capital of France?")


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
    # await main()
    

