"""
agent.py - Simple Runnable Agent
"""

import os
import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
import google.genai.types as types

from config import config

# -------------------------------
# CONFIG
# -------------------------------
APP_NAME = "ChatAgent"
USER_ID = "user"
SESSION_ID = "session1"

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

# -------------------------------
# AGENT
# -------------------------------
agent = LlmAgent(
    model=config.MODEL,
    name="ChatAgent",
    instruction="You are a helpful and precise assistant for general healthcare questions.",
)

# -------------------------------
# RUNNER SETUP
# -------------------------------
session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()

runner = Runner(
    agent=agent,
    app_name=APP_NAME,
    session_service=session_service,
    artifact_service=artifact_service,
)

# -------------------------------
# RUN FUNCTION
# -------------------------------
async def chat():
    # create session
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    while True:
        user_input = input("You: ")

        message = types.Content(
            role="user",
            parts=[types.Part(text=user_input)],
        )

        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=message,
        ):
            if event.is_final_response():
                print("Agent:", event.content.parts[0].text)
                break

# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    asyncio.run(chat())
