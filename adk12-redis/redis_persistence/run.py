"""
Custom ADK runner with Redis persistence and real Gemini responses
Run this instead of 'adk run' or 'adk web'
"""

import asyncio
import json
from google.genai.types import FunctionDeclaration, Tool
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from google import genai
from config import config
from agent_app.redis_session_service import RedisSessionService


# Configure Gemini API (assume config has GOOGLE_API_KEY)
client = genai.Client(api_key=config.GOOGLE_API_KEY)

async def run_agent_with_redis():
    print("=" * 70)
    print("ADK AGENT WITH REDIS PERSISTENCE - INTERACTIVE MODE")
    print("=" * 70)
    print()

    # Redis session service
    session_service = RedisSessionService(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        password=config.REDIS_PASSWORD,
        ttl=config.REDIS_TTL,
    )
    print(f"✅ Redis session service initialized: {config.REDIS_HOST}:{config.REDIS_PORT}")

    # IDs
    USER_ID = "test_user_001"
    SESSION_ID = "interactive-session-001"

    # Create session if not exists
    session = await session_service.get_session(SESSION_ID)
    if not session:
        await session_service.create_session(
            SESSION_ID,
            appName="redis_app", 
            userId=USER_ID
        )
        print(f"✅ Session created: {SESSION_ID}")
    else:
        print(f"✅ Session loaded: {SESSION_ID}")

    print()

    print("=" * 70)
    print("💬 Chat with Gemini AI (type 'quit' to exit)")
    print("=" * 70)
    print()

    # Define tools for state management
    get_state_decl = FunctionDeclaration(
        name="get_state",
        description="Retrieve a value from session state by key.",
        parameters={
            "type": "OBJECT",
            "properties": {"key": {"type": "STRING"}},
            "required": ["key"]
        }
    )

    set_state_decl = FunctionDeclaration(
        name="set_state",
        description="Store a key-value pair in session state.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING"},
                "value": {"type": "STRING"}
            },
            "required": ["key", "value"]
        }
    )

    tools = Tool(
        function_declarations=[get_state_decl, set_state_decl]
    )

    # Instruction
    instruction = """You are a helpful assistant.
Remember information the user tells you and recall it when asked.
Use the 'set_state' tool to store important facts (e.g., user's name as key 'name').
Use the 'get_state' tool to recall facts when needed."""

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue

        try:
            print("Agent: ", end="", flush=True)

            # Load session anew each turn to get latest state/events
            session = await session_service.get_session(SESSION_ID)

            # Build history from events (stored as json-serializable dicts)
            history = []
            for event_dict in session.events or []:
                parts = [types.Part(**p) for p in event_dict['parts']]
                history.append(types.Content(role=event_dict['role'], parts=parts))

            # Prepare configuration
            config_obj = types.GenerateContentConfig(
                system_instruction=instruction,
                tools=[tools]
            )

            # Send message and stream response
            response_stream = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=history + [types.Content(role='user', parts=[types.Part(text=user_input)])],
                config=config_obj
            )

            final_text = ""
            response = None
            for chunk in response_stream:
                if chunk.text:
                    final_text += chunk.text
                    print(chunk.text, end="", flush=True)
                response = chunk

            print()

            # Handle function calls
            continue_conversation = True
            current_history = history + [types.Content(role='user', parts=[types.Part(text=user_input)])]
            
            while continue_conversation:
                continue_conversation = False
                if response and response.candidates:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                continue_conversation = True
                                fc = part.function_call
                                function_name = fc.name
                                args = dict(fc.args)

                                # Execute the function
                                function_response = None
                                if function_name == "get_state":
                                    key = args["key"]
                                    function_response = session.state.get(key, None)
                                elif function_name == "set_state":
                                    key = args["key"]
                                    value = args["value"]
                                    session.state[key] = value
                                    function_response = "Stored successfully."

                                # Append function response
                                func_part = types.Part(
                                    function_response=types.FunctionResponse(
                                        name=function_name,
                                        response={"result": str(function_response)}
                                    )
                                )
                                func_content = types.Content(role="function", parts=[func_part])
                                current_history.append(candidate.content)
                                current_history.append(func_content)

                                # Generate next response
                                response_stream = client.models.generate_content_stream(
                                    model="gemini-1.5-flash",
                                    contents=current_history,
                                    config=config_obj
                                )
                                additional_text = ""
                                for chunk in response_stream:
                                    if chunk.text:
                                        additional_text += chunk.text
                                        print(chunk.text, end="", flush=True)
                                    response = chunk
                                print()
                                final_text += additional_text

            # Append user message and model response to history
            user_content = types.Content(role='user', parts=[types.Part(text=user_input)])
            model_content = types.Content(role='model', parts=[types.Part(text=final_text)])

            # Convert to dict for serialization
            session.events = session.events or []
            
            # Serialize Content objects properly
            user_dict = {
                'role': 'user',
                'parts': [{'text': user_input}]
            }
            model_dict = {
                'role': 'model',
                'parts': [{'text': final_text}]
            }
            
            session.events.append(user_dict)
            session.events.append(model_dict)

            # Update session in Redis (including updated state if set)
            await session_service.update_session(SESSION_ID, session.model_dump())

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print("Continuing...\n")
            continue

    # Summary
    print()
    print("=" * 70)
    print("📊 SESSION SUMMARY")
    print("=" * 70)

    session = await session_service.get_session(SESSION_ID)
    if session:
        print(f"Session ID   : {SESSION_ID}")
        print(f"App name     : {session.appName}")
        print(f"User ID      : {session.userId}")
        print(f"Events count : {len(session.events or [])}")
        print(f"State        : {session.state}")

    print()
    print("Done.")


if __name__ == "__main__":
    try:
        asyncio.run(run_agent_with_redis())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")

