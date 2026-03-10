# RedisAgent.py
import os
import asyncio
import redis.asyncio as redis
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
import google.genai.types as types

# Import the corrected service
from RedisDatabaseSessionService import RedisSessionService
from config import config

# -----------------------------
# Setup Constants
# -----------------------------
APP_NAME = "chatbot_demo"
USER_ID = "user_001"
SESSION_ID = "session_001"
MODEL = config.MODEL

# Set API Key directly for now or use your config
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

# -----------------------------
# Setup Redis Client
# -----------------------------
# decode_responses=True is crucial for our get_session logic to work
r_client = redis.from_url("redis://localhost:6379", decode_responses=True)
session_service = RedisSessionService(r_client)
artifact_service = InMemoryArtifactService()

# -----------------------------
# Create Agent and Runner
# -----------------------------
root_agent = LlmAgent(
    model=MODEL,
    name="ChatAgent",
    instruction="You are a helpful assistant. Respond politely and concisely."
)

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
    artifact_service=artifact_service
)

# -----------------------------
# Chat Function
# -----------------------------
async def chat(user_input):
    content = types.Content(
        role="user",
        parts=[types.Part(text=user_input)]
    )
    
    events = runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content
    )
    
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text
            print(f"ChatAgent: {text}")

# -----------------------------
# Main Execution Loop
# -----------------------------
async def main():
    # Verify session existence in Redis
    existing_session = await session_service.get_session(SESSION_ID)
    if not existing_session:
        print(f"Creating new Redis session: {SESSION_ID}")
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID # This will now be handled correctly by .pop()
        )
    else:
        print(f"Resuming existing Redis session: {SESSION_ID}")

    await chat("Hello! Can you suggest a fun weekend activity?")
    await chat("Give me a short summary of Artificial Intelligence.")

if __name__ == "__main__":
    asyncio.run(main())
