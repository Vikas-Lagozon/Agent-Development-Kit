import asyncio
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import callback_context
from google.adk.tools import base_tool
from google.adk.agents import callback_context




from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import agent_tool


APP_NAME = "state_tool_app"
USER_ID = "user1"
SESSION_ID = "session1"

# ---------------------------------------
# 1️⃣ Define Tool That Updates State
# ---------------------------------------
# The @tool decorator and CallbackContext are the standard way 
# to access session state within a tool.
@agent_tool
def track_user_action(context: callback_context) -> str:
    """Records a user action and increments the counter in session state."""
    
    # Update existing state
    # Use context.state.get() to safely handle the first run
    count = context.state.get("user_action_count", 0)
    context.state["user_action_count"] = count + 1

    # Add temporary state (temp: prefix means it won't persist across different user turns)
    context.state["temp:last_operation_status"] = "success"

    return f"Action recorded. Count = {count + 1}"


# ---------------------------------------
# 2️⃣ Create Agent
# ---------------------------------------
agent = Agent(
    model="gemini-1.5-flash",
    name="state_agent",
    tools=[track_user_action],
    instruction="""
    If the user says 'do action', call the track_user_action tool.
    Always report the current count to the user after calling the tool.
    """
)


# ---------------------------------------
# 3️⃣ Main Execution Logic
# ---------------------------------------
async def main():
    session_service = InMemorySessionService()

    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name=APP_NAME
    )

    # Create session with initial state
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state={}
    )

    print("--- Starting Agent Invocations ---")
    
    # Invoke agent multiple times to see state increment
    for i in range(3):
        print(f"\nTurn {i+1}:")
        response = await runner.run(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message="do action"
        )
        print("Agent:", response.output_text)

    # ---------------------------------------
    # 4️⃣ Check Final State
    # ---------------------------------------
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    print("\n--- Final Persisted State ---")
    # Note: 'temp:' keys will likely be gone here as the invocation ended
    print(session.state)

if __name__ == "__main__":
    asyncio.run(main())
