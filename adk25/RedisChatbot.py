# RedisChatbot.py
import os
import asyncio
import redis.asyncio as redis
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
import google.genai.types as types

from RedisDatabaseSessionService import RedisSessionService
from config import config

APP_NAME = "chatbot_demo"
USER_ID = "user_001"
SESSION_ID = "session_001"
MODEL = config.MODEL

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

# -----------------------------
# Redis & Services
# -----------------------------
r_client = redis.from_url("redis://localhost:6379", decode_responses=True)
session_service = RedisSessionService(r_client)
artifact_service = InMemoryArtifactService()

# -----------------------------
# Agent & Runner
# -----------------------------
root_agent = LlmAgent(
    model=MODEL,
    name="ChatAgent",
    instruction="You are a helpful assistant. Respond naturally, politely, and concisely."
)

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
    artifact_service=artifact_service
)

# -----------------------------
# Conversation State
# -----------------------------
conversation_history = []  # Keep track of messages in memory

async def chat(user_input: str) -> str:
    # Add user message to history
    conversation_history.append(types.Content(role="user", parts=[types.Part(text=user_input)]))
    
    # Build a combined message content for ADK
    # ADK Runner can accept a single 'new_message' and will use session to maintain previous context
    content = types.Content(
        role="user",
        parts=[types.Part(text=user_input)]
    )
    
    events = runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content
    )
    
    response_text = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text
            print(f"ChatAgent: {response_text}")
            # Append assistant reply to history
            conversation_history.append(types.Content(role="assistant", parts=[types.Part(text=response_text)]))
    return response_text

# -----------------------------
# Interactive Loop
# -----------------------------
async def conversation_loop():
    print("=== ChatBot Interactive Session ===")
    print("Type 'exit' to quit.\n")
    
    # Ensure session exists
    existing_session = await session_service.get_session(SESSION_ID)
    if not existing_session:
        print(f"Creating new Redis session: {SESSION_ID}")
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )
    else:
        print(f"Resuming existing Redis session: {SESSION_ID}")
    
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("Ending chat session.")
            break
        if user_input:
            await chat(user_input)

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    asyncio.run(conversation_loop())
