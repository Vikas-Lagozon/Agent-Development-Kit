# Root Agent A2A Server

import os
from google.adk.agents.llm_agent import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
import uvicorn
from config import config


# ---------------------------------
# Configuration
# ---------------------------------
MODEL = config.MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()


# ---------------------------------
# Root Agent Definition
# ---------------------------------
root_agent = Agent(
    model=MODEL,
    name="root_agent",
    description="Main assistant that interacts with users.",
    instruction="""
You are a helpful AI assistant.

Your responsibilities:
- Greet users
- Answer questions clearly
- Provide helpful explanations
- Assist with general tasks

Always respond in a friendly and professional way.
"""
)


# ---------------------------------
# A2A Agent Card
# ---------------------------------
agent_card = AgentCard(
    name="root_agent",
    url="http://localhost:8001",
    description="Root assistant agent exposed through A2A",
    version="1.0.0",
    capabilities={},
    skills=[],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=False,
)


# ---------------------------------
# Convert Agent → A2A Application
# ---------------------------------
a2a_app = to_a2a(
    agent=root_agent,
    port=8001,
    agent_card=agent_card
)


# -------------
# Start A2A Server using Uvicorn
# -------------
if __name__ == "__main__":
    print("Starting A2A server (use CTRL+C to stop)…")
    uvicorn.run(
        a2a_app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
