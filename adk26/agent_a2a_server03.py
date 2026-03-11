# Root Agent A2A Server

import os
from google.adk.agents.llm_agent import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from config import config
from pathlib import Path
import sys
import uvicorn

# -----------------------------
# Configuration
# -----------------------------
MODEL = config.MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

# -----------------------------
# Root Agent Definition
# -----------------------------
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

# -----------------------------
# Load A2A AgentCard from JSON
# -----------------------------
agent_card_path = Path(r"D:\Agent-Development-Kit\adk26\agent-card.json")

if not agent_card_path.is_file():
    print(f"Error: Agent card file not found: {agent_card_path}")
    sys.exit(1)

# -----------------------------
# Wrap Agent with A2A
# -----------------------------
a2a_app = to_a2a(
    agent=root_agent,
    port=8001,
    agent_card=str(agent_card_path)  # Path to JSON file
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
