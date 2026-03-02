# chatbot.py

import os
import asyncio
from google.adk.agents import Agent
from google.adk.sessions import DatabaseSessionService
from google.adk import Runner
import google.genai.types as types
from config import config

# -----------------------------
# Constants
# -----------------------------
APP_NAME = "Jarvis"
USER_ID = "user_001"
SESSION_ID = "session_001"
MODEL = "gemini-2.5-flash"

# -----------------------------
# Ensure API Key Mode
# -----------------------------
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# -----------------------------
# System Instruction
# -----------------------------
SYSTEM_INSTRUCTION = """
You are a helpful and professional assistant.
Responsibilities:
- Maintain context from previous messages in the same session.
- Respond concisely, clearly, and politely.
- If you do not know the answer, admit it.
"""

# -----------------------------
# Create Persistent Agent
# -----------------------------
chat_agent = Agent(
    name="persistent_chat_agent",
    model=MODEL,
    description="A chatbot that stores conversations in Postgres.",
    instruction=SYSTEM_INSTRUCTION,
)

# -----------------------------
# Database Session Service
# -----------------------------
session_service = DatabaseSessionService(
    db_url=config.SQLALCHEMY_DATABASE_URI,
    connect_args={
        "server_settings": {
            "search_path": config.DB_SCHEMA
        }
    }
)

# -----------------------------
# Runner
# -----------------------------
runner = Runner(
    app_name=APP_NAME,
    agent=chat_agent,
    session_service=session_service
)

print("Chatbot initialized successfully!")
print(f"Using PostgreSQL schema: {config.DB_SCHEMA}")

# -----------------------------
# Ensure session exists (safe get/create)
# -----------------------------
async def get_or_create_session(app_name, user_id, session_id):
    # Try to get an existing session
    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    if session is None:
        # Create session only if it doesn’t exist
        session = await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
    return session

# -----------------------------
# Chat function
# -----------------------------
async def chat(
    user_input: str,
    session_id: str = SESSION_ID,
    user_id: str = USER_ID
):
    """
    Send a message to the chatbot and get the response.
    Maintains history in Postgres via DatabaseSessionService.
    """
    # Ensure the session exists (get or create)
    await get_or_create_session(APP_NAME, user_id, session_id)

    # Build Content
    content = types.Content(
        role="user",
        parts=[types.Part(text=user_input)]
    )

    # Send message to runner
    events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content
    )

    final_response = None
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text
            print("ChatAgent:", final_response)

    return final_response

# -----------------------------
# Interactive CLI / Jupyter
# -----------------------------
async def main():
    print("\n--- Persistent Chatbot ---")
    print("Type 'exit' to quit.\n")

    # Ensure session exists before first message
    await get_or_create_session(APP_NAME, USER_ID, SESSION_ID)

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await chat(user_input)

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    asyncio.run(main())