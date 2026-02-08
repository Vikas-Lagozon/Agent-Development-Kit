"""
Agent definitions for ADK Web and CLI usage.

IMPORTANT:
- Agents must be defined at module level
- No async calls here
- No session creation here
"""

import os
import logging

from google.adk.agents import Agent
from google.adk.tools.google_search_tool import google_search

# --------------------------------------------------
# Environment & logging safety
# --------------------------------------------------
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

logging.getLogger("google.adk.runners").setLevel(logging.ERROR)
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

# --------------------------------------------------
# Research Agent
# --------------------------------------------------
research_instruction = """
You are a market research agent for an e-commerce site.

When a user provides a shopping intent:
- Use Google Search to understand popular products
- Generate EXACTLY 5 concise product search queries
- Return ONLY the list of queries
"""

root_agent = Agent(
    model="gemini-2.0-flash",
    name="research_agent",
    description="Researches shopping trends and generates product queries.",
    instruction=research_instruction,
    tools=[google_search],
)

agent = root_agent