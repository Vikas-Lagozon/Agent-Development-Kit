# research.py
# ─────────────────────────────────────────────────────────────
# Research Agent Module
# ─────────────────────────────────────────────────────────────

from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from config import config

# ── Model ─────────────────────────────────────────────────────
RESEARCH_MODEL = config.RESEARCH_MODEL

# ── Agent ─────────────────────────────────────────────────────
research_agent = Agent(
    model=RESEARCH_MODEL,
    name="deep_topic_research_agent",
    description=(
    "Performs deep, up-to-date topic research using Gemini's built-in web retrieval. "
    "Use this agent for recent events, breaking news, current statistics, "
    "market trends, recent releases, policy updates, or any topic requiring live information."
    ),

    instruction="""
    You are an expert research analyst with Gemini's built-in web retrieval.

    When given a topic or question:

    1. Retrieve the most recent and relevant information automatically.
    2. Prioritize authoritative, high-quality, and recent sources.
    3. Cross-check important facts when possible.
    4. Synthesize findings into a detailed, well-structured research report (500–1500 words).
    5. Use clear headings and bullet points where appropriate.
    6. Include source attributions or references for key facts.
    7. Focus on clarity, depth, accuracy, and neutrality.

    Output ONLY the research content.
    Do not include preamble, explanations about your process, or meta-commentary.
    """
)

# ── App (for standalone adk run / adk web usage) ─────────────
research_app = App(
    name="research_agent",
    root_agent=research_agent,
)

