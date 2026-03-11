# a2a_root/root_agent/agent.py

import os
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from .config import config

MODEL = config.MODEL
GOOGLE_API_KEY = config.GOOGLE_API_KEY

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

# --------------------------------------------------
# Remote A2A Agent (Client Proxy)
# --------------------------------------------------
hello_world_agent = RemoteA2aAgent(
    name="hello_world_agent",
    description="Remote agent that rolls dice and checks primes",
    agent_card=f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}"
)

# --------------------------------------------------
# Root LLM Agent
# --------------------------------------------------
root_agent = LlmAgent(
    model=MODEL,
    name="root_agent",
    description="Root agent that delegates tasks to remote agents",
    instruction="""
You are the Root Agent.

If the user asks to:
- roll a dice
- check if numbers are prime

delegate the task to the hello_world_agent.

For other questions, answer normally.
""",
    sub_agents=[hello_world_agent]
)
