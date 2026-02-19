"""
Custom ADK runner with Redis persistence and real Gemini responses
Run this instead of 'adk run' or 'adk web'
"""

import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from config import config
from agent_app.redis_session_service import RedisSessionService


async def run_agent_with_redis():
    print("=" * 70)
    print("🚀 ADK AGENT WITH REDIS PERSISTENCE - INTERACTIVE MODE")
    print("=" * 70)
    print()

    # 1. Initialize Redis session service
    session_service = RedisSessionService(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        password=config.REDIS_PASSWORD,
        ttl=config.REDIS_TTL,
    )
    print(f"✅ Redis session service initialized: {config.REDIS_HOST}:{config.REDIS_PORT}")

    # 2. Define IDs
    USER_ID = "test_user_001"
    SESSION_ID = "interactive-session-001"

    # 3. Initialize Agent
    agent = LlmAgent(
        name="RedisGeminiAgent",
        model="gemini-2.5-flash", 
        description="Gemini agent with Redis-backed session persistence.",
        instruction="""You are a helpful assistant. 
Remember information the user tells you and recall it when asked.
You can store important facts in session.state if needed.""",
    )
    print(f"✅ Agent '{agent.name}' loaded")

    # 4. Create Runner
    # The Runner coordinates between the Agent and the SessionService
    runner = Runner(
        agent=agent,
        app_name="redis_persistence_app",
        session_service=session_service,
    )
    print("✅ Runner created with Redis session service")
    print(f"✅ Session loaded: {SESSION_ID}")

    print("\n" + "=" * 70)
    print("💬 Chat with Gemini AI (type 'quit' to exit)")
    print("=" * 70)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                break

            if not user_input:
                continue

            # 5. Prepare the user message using the GenAI types
            user_message = types.Content(
                role="user",
                parts=[types.Part(text=user_input)]
            )

            print("Agent: ", end="", flush=True)

            # 6. Run the agent via the Runner
            # NOTE: The Runner automatically appends 'user_message' and the
            # final agent response to the session history in Redis.
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=user_message
            ):
                # Print the streaming response as it arrives
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(part.text, end="", flush=True)

            print() # New line after the complete response

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Final Summary
    print("\n" + "=" * 70)
    print("📊 SESSION SUMMARY")
    print("=" * 70)

    session = await session_service.get_session(SESSION_ID)
    if session:
        print(f"Session ID   : {SESSION_ID}")
        print(f"User ID      : {session.user_id}")
        print(f"Events count : {len(session.events or [])}")
        print(f"State        : {session.state}")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(run_agent_with_redis())