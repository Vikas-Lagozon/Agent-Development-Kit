"""Google Search Agent definition for ADK Gemini Live API Toolkit demo."""
import os
from google.adk.agents import Agent
from google.adk.tools import google_search
from config import config

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_GENAI_API_VERSION"] = "v1beta"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# Default models for Live API with native audio support:
# - Gemini Live API: gemini-2.5-flash-native-audio-preview-12-2025
# - Vertex AI Live API: gemini-live-2.5-flash-native-audio
agent = Agent(
    name="google_search_agent",
    model="gemini-2.5-flash-native-audio-preview-12-2025",
    tools=[google_search],
    instruction="You are a helpful assistant that can search the web."
)
