# a2a_root/root_agent/agent.py
#
# Root ADK agent that delegates to:
#   • hello_world_agent  (port 8001) — dice rolling + prime checking
#   • blog_writing_agent (port 8002) — LangGraph technical blog writer
# ─────────────────────────────────────────────────────────────────────────────

import os
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from .config import config

MODEL = config.MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

# ── Remote Agent 1: ADK hello_world (dice + primes) ──────────────────────────
hello_world_agent = RemoteA2aAgent(
    name="hello_world_agent",
    description="Remote agent that rolls dice and checks prime numbers",
    agent_card=f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}",
    timeout=1800.0,  # 30 minutes — dice/prime tasks are fast
)

# ── Remote Agent 2: LangGraph blog writer ────────────────────────────────────
blog_writing_agent = RemoteA2aAgent(
    name="blog_writing_agent",
    description=(
        "LangGraph agent that writes full technical blog posts in Markdown. "
        "Supports explainers, tutorials, news roundups, comparisons, and system-design posts. "
        "Can optionally research the web for up-to-date information."
    ),
    agent_card=f"http://localhost:8002{AGENT_CARD_WELL_KNOWN_PATH}",
    timeout=3600.0,  # 60 minutes — blog pipeline can take a long time
)

# ── Root LLM Agent ────────────────────────────────────────────────────────────
root_agent = LlmAgent(
    model=MODEL,
    name="root_agent",
    description="Root agent that delegates tasks to specialised remote agents",
    instruction="""
You are the Root Agent. Your job is to understand the user's intent and
route the request to the correct specialist agent.

─── Routing rules ───────────────────────────────────────────────────────────

1. hello_world_agent  →  delegate when the user asks to:
   - Roll a die / dice (e.g. "roll a 6-sided die")
   - Check whether a number or list of numbers is prime

2. blog_writing_agent  →  delegate when the user asks to:
   - Write a blog post / article / tutorial
   - Write a technical explainer on any topic
   - Write a news roundup (e.g. "latest AI news this week")
   - Write a comparison or system-design post
   - Anything phrased as "Write a blog on X" or "Write about X"

3. Answer directly for everything else (greetings, general questions, etc.)

─── Important ───────────────────────────────────────────────────────────────
- When delegating to blog_writing_agent, forward the FULL user request as-is
  so the blog agent receives the exact topic/instructions.
- Do NOT attempt to write blog posts yourself.
""",
    sub_agents=[hello_world_agent, blog_writing_agent],
)



# adk web a2a_root/