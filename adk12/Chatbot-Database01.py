import os
import asyncio
from config import config

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types


# -------------------------------------------------
# Configuration
# -------------------------------------------------
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

APP_NAME = "db_chatbot_app"
USER_ID = "user_1"
SESSION_ID = "session_001"

# SQLite async URL
db_url = "sqlite+aiosqlite:///./db_agent_data.db"


# -------------------------------------------------
# Create Agent
# -------------------------------------------------
agent = LlmAgent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="""
You are a helpful AI assistant.
Keep responses clear and conversational.
"""
)


# -------------------------------------------------
# Main Async Function
# -------------------------------------------------
async def main():

    # 1️⃣ Create Database Session Service
    session_service = DatabaseSessionService(db_url=db_url)

    # 🔥 Ensure tables exist (safe for most versions)
    if hasattr(session_service, "initialize"):
        await session_service.initialize()

    # 2️⃣ Create or Load Session
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    if not session:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
            state={"conversation_started": True}
        )

    # 3️⃣ Create Runner
    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name=APP_NAME
    )

    print("\n================ CHATBOT STARTED ================\n")

    # 4️⃣ Interactive Conversation
    while True:

        message = input("👤 User: ")

        if message.lower() in ["", "exit", "quit"]:
            break

        print("🤖 Assistant: ", end="", flush=True)

        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=message)]
            )
        ):
            if event.content and event.content.parts:
                print(event.content.parts[0].text, end="", flush=True)

        print("\n")

    print("\n================ CHATBOT ENDED ================\n")

    # 5️⃣ Inspect Final Session
    final_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    print("\n--- Final Session State ---")
    print("Session ID:", final_session.id)
    print("State:", final_session.state)
    print("Total Events:", len(final_session.events))
    print("---------------------------------\n")


# -------------------------------------------------
# Run App
# -------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())

