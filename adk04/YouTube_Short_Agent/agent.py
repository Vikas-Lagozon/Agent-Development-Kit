import asyncio
from dotenv import load_dotenv, find_dotenv

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import google_search
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

from google.genai import types

from YouTube_Short_Agent.util import load_instructions_from_file

# ------------------------------------------------------------------
# ENV
# ------------------------------------------------------------------
load_dotenv(find_dotenv())

MODEL = "gemini-2.5-pro"

APP_NAME = "YouTube Short Creator"
USER_ID = "user_123"
SESSION_ID = "session_123"

# ------------------------------------------------------------------
# SUB AGENTS
# ------------------------------------------------------------------

scriptwriter_agent = LlmAgent(
    name="ScriptWriterAgent",
    model=MODEL,
    instruction=load_instructions_from_file("scriptwriter_instruction.txt"),
    tools=[google_search],
    output_key="generated_script",
)

visualizer_agent = LlmAgent(
    name="ShortVisualizerAgent",
    model=MODEL,
    instruction=load_instructions_from_file("visualizer_instruction.txt"),
    description="Generates visual concepts based on the provided script.",
    output_key="generated_visuals",
)

formatter_agent = LlmAgent(
    name="ShortFormatterAgent",
    model=MODEL,
    instruction=(
        "Combine state['generated_script'] and "
        "state['generated_visuals'] into a formatted YouTube Short."
    ),
    description="Formats final YouTube Short output.",
    output_key="final_short_concept",
)

# ------------------------------------------------------------------
# ROOT LOOP AGENT
# ------------------------------------------------------------------

root_agent = LoopAgent(
    name="YouTubeShortAgent",
    max_iterations=3,
    sub_agents=[
        scriptwriter_agent,
        visualizer_agent,
        formatter_agent,
    ],
    description="Researches, writes, visualizes, and formats YouTube Shorts."
)

# ------------------------------------------------------------------
# RUNNER LOGIC (ASYNC – REQUIRED)
# ------------------------------------------------------------------

async def call_agent(query: str):
    session_service = InMemorySessionService()

    await session_service.create_session(
        session_id=SESSION_ID,
        user_id=USER_ID,
        app_name=APP_NAME,
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=query)],
    )

    events = runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    )

    for event in events:
        if event.is_final_response():
            print("\nFINAL YOUTUBE SHORT CONCEPT\n")
            print(event.content.parts[0].text)


# ------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(
        call_agent("I want to write a short on 'how to build AI Agents'")
    )




# (venv) D:\Agent-Development-Kit\adk04>python -m YouTube_Short_Agent.agent

