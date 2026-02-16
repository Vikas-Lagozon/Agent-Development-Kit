# ============================================================
# After Model Callback Example (Fixed & Production Ready)
# ============================================================

import os
import asyncio
from typing import Optional
from copy import deepcopy

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.models import LlmResponse
from google.genai import types

from config import config

# ------------------------------------------------------------
# Environment Setup
# ------------------------------------------------------------
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

APP_NAME = "guardrail_app"
USER_ID = "user_1"
SESSION_ID = "session_001"

MODEL_NAME = "gemini-2.5-flash"


# ============================================================
# AFTER MODEL CALLBACK
# ============================================================

def simple_after_model_modifier(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """
    Inspect/modify the LLM response after model execution.
    """

    print(f"\n[Callback] After model call for agent: {callback_context.agent_name}")

    # --------------------------------------------------------
    # Validate response structure safely
    # --------------------------------------------------------
    if not llm_response:
        print("[Callback] Empty LlmResponse.")
        return None

    if llm_response.error_message:
        print(f"[Callback] Error detected: {llm_response.error_message}")
        return None

    if not llm_response.content or not llm_response.content.parts:
        print("[Callback] No content parts found.")
        return None

    first_part = llm_response.content.parts[0]

    # Skip if function call
    if getattr(first_part, "function_call", None):
        print("[Callback] Response contains function call. Skipping modification.")
        return None

    original_text = first_part.text or ""
    print(f"[Callback] Original text snippet: {original_text[:100]}")

    # --------------------------------------------------------
    # Modification Logic
    # --------------------------------------------------------
    search_term = "joke"
    replace_term = "funny story"

    if search_term in original_text.lower():
        print(f"[Callback] Found '{search_term}'. Modifying response.")

        # Case-insensitive replacement
        modified_text = original_text.replace("joke", "funny story")
        modified_text = modified_text.replace("Joke", "Funny story")

        # Deep copy parts
        modified_parts = [deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = modified_text

        new_response = LlmResponse(
            content=types.Content(
                role="model",
                parts=modified_parts
            ),
            grounding_metadata=llm_response.grounding_metadata
        )

        print("[Callback] Returning modified response.")
        return new_response

    print("[Callback] No modification needed.")
    return None


# ============================================================
# AGENT DEFINITION
# ============================================================

my_llm_agent = LlmAgent(
    name="AfterModelCallbackAgent",
    model=MODEL_NAME,
    instruction="You are a helpful assistant.",
    description="Demonstrates after_model_callback",
    after_model_callback=simple_after_model_modifier,
)


# ============================================================
# SETUP (Create Once)
# ============================================================

async def setup():
    session_service = InMemorySessionService()

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    runner = Runner(
        agent=my_llm_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    return runner


# ============================================================
# CALL AGENT
# ============================================================

async def call_agent(runner: Runner, query: str):
    print(f"\nUSER: {query}")

    content = types.Content(
        role="user",
        parts=[types.Part(text=query)]
    )

    events = runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content
    )

    async for event in events:
        if event.is_final_response():
            print("AGENT:", event.content.parts[0].text)


# ============================================================
# MAIN FLOW
# ============================================================

async def main():
    runner = await setup()

    # Turn 1
    await call_agent(runner, 'Write the word "joke" multiple times.')

    # Turn 2
    await call_agent(runner, "Tell me a joke about programming.")

    # Turn 3
    await call_agent(runner, "Say hello.")


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
    # await main()
