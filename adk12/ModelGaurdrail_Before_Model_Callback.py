# ============================================================
# Guardrail App with before_model_callback (Robust Version)
# ============================================================

import os
import asyncio
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
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


# ------------------------------------------------------------
# BEFORE MODEL CALLBACK (Fixed Safely)
# ------------------------------------------------------------
def simple_before_model_modifier(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:

    print(f"\n[Callback] Agent: {callback_context.agent_name}")

    # --------------------------------------------------------
    # Extract last user message
    # --------------------------------------------------------
    last_user_message = ""
    if llm_request.contents and llm_request.contents[-1].role == "user":
        if llm_request.contents[-1].parts:
            last_user_message = llm_request.contents[-1].parts[0].text

    print(f"[Callback] Last user message: {last_user_message}")

    # --------------------------------------------------------
    # Handle system instruction safely (str OR Content)
    # --------------------------------------------------------
    original_instruction = llm_request.config.system_instruction

    prefix = "[Modified by Callback] "

    # Case 1: If instruction is string
    if isinstance(original_instruction, str):
        modified_instruction = prefix + original_instruction
        llm_request.config.system_instruction = modified_instruction

    # Case 2: If instruction is Content
    elif isinstance(original_instruction, types.Content):
        if not original_instruction.parts:
            original_instruction.parts = [types.Part(text="")]

        original_text = original_instruction.parts[0].text or ""
        original_instruction.parts[0].text = prefix + original_text
        llm_request.config.system_instruction = original_instruction

    # Case 3: If None
    else:
        llm_request.config.system_instruction = prefix

    print("[Callback] System instruction modified")

    # --------------------------------------------------------
    # BLOCK Logic
    # --------------------------------------------------------
    if "BLOCK" in last_user_message.upper():
        print("[Callback] BLOCK detected → Skipping model call")

        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text="LLM call was blocked by before_model_callback."
                    )
                ],
            )
        )

    print("[Callback] Proceeding to model")
    return None


# ------------------------------------------------------------
# Create Agent
# ------------------------------------------------------------
my_llm_agent = LlmAgent(
    name="ModelCallbackAgent",
    model=MODEL_NAME,
    instruction="You are a helpful assistant.",
    description="Demonstrates before_model_callback",
    before_model_callback=simple_before_model_modifier,
)


# ------------------------------------------------------------
# Setup Session + Runner
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# Call Agent
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
async def main():
    runner = await setup()

    await call_agent(runner, "Write a short joke.")
    await call_agent(runner, "Write a joke on BLOCK")
    await call_agent(runner, "Tell me something motivational.")


# ------------------------------------------------------------
# Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
    # await main()


