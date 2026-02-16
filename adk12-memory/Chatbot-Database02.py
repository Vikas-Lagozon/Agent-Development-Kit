import os
import asyncio
import uuid
from config import config

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types


# -------------------------------------------------
# Configuration
# -------------------------------------------------
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

APP_NAME = "chat_db"
db_url = "sqlite+aiosqlite:///./agent_data.db"


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
# Utility: Ensure Session Exists
# -------------------------------------------------
async def ensure_session(session_service, user_id, session_id):
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id
    )

    if not session:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state={"conversation_started": True}
        )


# -------------------------------------------------
# Main Async Function
# -------------------------------------------------
async def main():

    # 1️⃣ Create Database Session Service
    session_service = DatabaseSessionService(db_url=db_url)

    # Ensure DB tables exist (version-safe)
    if hasattr(session_service, "initialize"):
        await session_service.initialize()

    # 2️⃣ Create Runner
    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name=APP_NAME
    )

    # Default User & Session
    current_user = "user_1"
    current_session = "session_001"

    await ensure_session(session_service, current_user, current_session)

    print("\n=========== MULTI USER / MULTI SESSION CHATBOT ===========\n")
    print("Commands:")
    print("  /user <user_id>        → Switch user")
    print("  /session <session_id>  → Switch session")
    print("  /new <session_id>      → Create new session")
    print("  /auto                  → Create auto session (UUID)")
    print("  /exit                  → Quit\n")

    # 3️⃣ Interactive Loop
    while True:

        print(f"\n(User: {current_user} | Session: {current_session})")
        message = input("👤 User: ")

        if message.lower() in ["", "/exit", "exit", "quit"]:
            break

        # 🔁 Switch User
        if message.startswith("/user"):
            parts = message.split()
            if len(parts) == 2:
                current_user = parts[1]
                print(f"✅ Switched to user: {current_user}")
                await ensure_session(session_service, current_user, current_session)
            else:
                print("Usage: /user <user_id>")
            continue

        # 🔁 Switch Session
        if message.startswith("/session"):
            parts = message.split()
            if len(parts) == 2:
                current_session = parts[1]
                print(f"✅ Switched to session: {current_session}")
                await ensure_session(session_service, current_user, current_session)
            else:
                print("Usage: /session <session_id>")
            continue

        # ➕ Create New Session
        if message.startswith("/new"):
            parts = message.split()
            if len(parts) == 2:
                current_session = parts[1]
                await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=current_user,
                    session_id=current_session,
                    state={"conversation_started": True}
                )
                print(f"✅ New session created: {current_session}")
            else:
                print("Usage: /new <session_id>")
            continue

        # 🔥 Auto-Generate Session ID
        if message.startswith("/auto"):
            current_session = f"session_{uuid.uuid4().hex[:8]}"
            await session_service.create_session(
                app_name=APP_NAME,
                user_id=current_user,
                session_id=current_session,
                state={"conversation_started": True}
            )
            print(f"✅ Auto-created session: {current_session}")
            continue

        # 💬 Normal Conversation
        print("🤖 Assistant: ", end="", flush=True)

        async for event in runner.run_async(
            user_id=current_user,
            session_id=current_session,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=message)]
            )
        ):
            if event.content and event.content.parts:
                print(event.content.parts[0].text, end="", flush=True)

        print("\n")

    print("\n================ CHATBOT ENDED ================\n")


# -------------------------------------------------
# Run App
# -------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())

