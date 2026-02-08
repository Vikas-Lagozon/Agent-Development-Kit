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
from tools import find_shopping_items

# --------------------------------------------------
# Environment & logging safety
# --------------------------------------------------
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

logging.getLogger("google.adk.runners").setLevel(logging.ERROR)
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

# --------------------------------------------------
# Shopping Agent
# --------------------------------------------------
shop_instruction = """
You are a shopping concierge for an e-commerce site.

Responsibilities:
1. Accept a list of product search queries
2. Use the `find_shopping_items` tool
3. Present results with product name, description, and image URL
"""

root_agent = Agent(
    model="gemini-2.0-flash",
    name="shop_agent",
    description="Finds and presents products from the catalog.",
    instruction=shop_instruction,
    tools=[find_shopping_items],
)

agent = root_agent