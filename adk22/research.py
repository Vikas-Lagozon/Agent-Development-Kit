# research.py
# ─────────────────────────────────────────────────────────────
# Research Agent Module (With Google Search + Current Date/Time Tool)
# ─────────────────────────────────────────────────────────────

import os
import datetime
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from google.adk.tools.google_search_tool import google_search
from config import config
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import uvicorn
# ── CONFIG ────────────────────────────────────────────────────
APP_NAME = "research_agent_app"
RESEARCH_MODEL = config.RESEARCH_MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

# # ── CUSTOM TOOL: get_current_datetime ────────────────────────
# def get_current_datetime() -> str:
#     """
#     Returns the current date, time, and day of the week.
#     Use this whenever the user asks for the current date or time.
#     """
#     now = datetime.datetime.now()
#     return now.strftime("%A, %B %d, %Y, %I:%M %p")

# # ── SEARCH SPECIALIST (Built-in Tool Only) ───────────────────
# # This agent handles the Google Search tool exclusively to avoid the 400 error.
search_specialist = LlmAgent(
    name="google_search_specialist",
    model=RESEARCH_MODEL,
    instruction="""
    You are a web search expert. 
    Your ONLY job is to use the google_search tool to find accurate, up-to-date information 
    on the requested topic and provide the raw findings to the requester.
    """,
    tools=[google_search],
)

# ── RESEARCH AGENT (Orchestrator) ────────────────────────────
# This agent uses the custom Python tool and delegates searching to the specialist.
research_agent = LlmAgent(
    name="research_agent",
    model=RESEARCH_MODEL,
    instruction="""
You are a deep research analyst. 

When given a topic or question:
1. If you need live information, use the `Google Search_specialist` tool.
2. If the user asks for the current date or time, use the `get_current_datetime` tool.
3. Prioritize authoritative, high-quality, and recent sources.
4. Synthesize findings into a detailed research report (500–1500 words).
5. Use clear headings and bullet points.
6. Include source references for key facts.

Output ONLY the research content. Do not include preamble or meta-commentary.
""",
    tools=[
        AgentTool(agent=search_specialist)# Wrapper for the search agent
    ],
)

a2a_app = to_a2a(research_agent)

if __name__ =="__main__":
    uvicorn.run(a2a_app,host = "0.0.0.0",port = 8005)