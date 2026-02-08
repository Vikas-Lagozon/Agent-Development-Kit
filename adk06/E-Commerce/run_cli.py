"""
CLI runner for local testing.

This file:
- Creates sessions
- Runs agents manually
- Is NOT used by ADK Web
"""

import os
import asyncio
from dotenv import load_dotenv, find_dotenv

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

from agents import research_agent, shop_agent

# --------------------------------------------------
# Environment
# --------------------------------------------------
load_dotenv(find_dotenv())

if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

# --------------------------------------------------
# Constants
# --------------------------------------------------
APP_NAME = "ecommerce_agent"
USER_ID = "user_123"
SESSION_ID = "session_123"

# --------------------------------------------------
# Helper: run agent once
# --------------------------------------------------
async def run_agent_once(agent, query, session_service):
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        if event.is_final_response():
            return event.content.parts[0].text if event.content else None

# --------------------------------------------------
# Main
# --------------------------------------------------
async def main():
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    print("\n--- Research Agent ---")
    research_output = await run_agent_once(
        research_agent,
        "Birthday present for a 10 year old boy",
        session_service,
    )
    print(research_output)

    print("\n--- Shop Agent ---")
    shop_output = await run_agent_once(
        shop_agent,
        f"Find items for these queries:\n{research_output}",
        session_service,
    )
    print(shop_output)

# --------------------------------------------------
# Entrypoint
# --------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
