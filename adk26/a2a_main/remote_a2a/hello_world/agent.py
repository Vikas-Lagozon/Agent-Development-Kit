# Remote Hello World Agent using LlmAgent + FunctionTool
# D:\Agent-Development-Kit\adk26\a2a_main\remote_a2a\hello_world\agent.py
import random
import os
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
from .config import config

MODEL = config.MODEL
GOOGLE_API_KEY = config.GOOGLE_API_KEY

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

# ----------------------
# Tool Functions
# ----------------------
def roll_die(sides: int, tool_context=None) -> int:
    """Roll a die and return the result."""
    return random.randint(1, sides)

async def check_prime(nums: list[int], tool_context=None) -> str:
    """Check if numbers are prime."""
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n**0.5)+1):
            if n % i == 0:
                return False
        return True
    results = {n: is_prime(n) for n in nums}
    return str(results)

# ----------------------
# Wrap Tools using FunctionTool
# ----------------------
roll_die_tool = FunctionTool(roll_die)
check_prime_tool = FunctionTool(check_prime)

# ----------------------
# Remote LlmAgent
# ----------------------
hello_world_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="hello_world_agent",
    description="Hello world agent that can roll a dice and check prime numbers",
    instruction="""
You are a Hello World agent.

- When asked to roll a die, call the roll_die tool with integer sides.
- When asked to check primes, call check_prime with a list of integers.
- Always use tools; never calculate primes or rolls manually.
""",
    tools=[roll_die_tool, check_prime_tool]  # FunctionTools go in a list
)

# ----------------------
# Agent Card
# ----------------------
agent_card = AgentCard(
    name="hello_world_agent",
    url="http://localhost:8001",
    description="Hello World Agent with dice rolling and prime checking tools",
    version="0.0.1",
    capabilities={},
    skills=[
        {
            "id": "hello_world_agent",
            "name": "model",
            "description": "Hello World LLM model",
            "tags": ["llm"]
        },
        {
            "id": "hello_world_agent-roll_die",
            "name": "roll_die",
            "description": "Roll a die tool",
            "tags": ["llm","tools"]
        },
        {
            "id": "hello_world_agent-check_prime",
            "name": "check_prime",
            "description": "Check prime numbers tool",
            "tags": ["llm","tools"]
        }
    ],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=False
)

# ----------------------
# Create A2A Application
# ----------------------
a2a_app = to_a2a(
    agent=hello_world_agent,
    port=8001,
    agent_card=agent_card
)

# uvicorn remote_a2a.hello_world.agent:a2a_app --host localhost --port 8001
