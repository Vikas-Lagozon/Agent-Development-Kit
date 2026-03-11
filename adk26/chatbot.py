import os
import asyncio
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
import google.genai.types as types
from config import config

# -----------------------------
# Setup API Key and model
# -----------------------------
APP_NAME = "chatbot_demo"
USER_ID = "user_001"
SESSION_ID = "session_001"
MODEL = "gemini-2.5-flash"

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

# -----------------------------
# Create LlmAgent (chatbot)
# -----------------------------
root_agent = LlmAgent(
    model=MODEL,
    name="ChatAgent",
    instruction="""
    You are a helpful assistant. Respond politely and concisely to user questions.
    """
)

# -----------------------------
# Setup In-Memory Services
# -----------------------------
session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()

# Create a new session
session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
)

# -----------------------------
# Setup Runner
# -----------------------------
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
    artifact_service=artifact_service
)

# -----------------------------
# Chat function
# -----------------------------
async def chat(user_input):
    content = types.Content(
        role="user",
        parts=[types.Part(text=user_input)]
    )
    
    events = runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content
    )
    
    async for event in events:
        # Print final response only
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text
            print("ChatAgent:", text)

# -----------------------------
# Chat
# -----------------------------
chat("Hello! Can you suggest a fun weekend activity?")
chat("Give me a short summary of Artificial Intelligence.")
