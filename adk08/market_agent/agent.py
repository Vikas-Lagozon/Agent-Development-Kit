from google.adk.agents import LlmAgent

from market_agent.prompt import DESCRIPTION, INSTRUCTIONS

# BigQuery tool
from market_agent.tools.bigquery_tool import (
    get_cloud_security_performance
)

# Google Search tool (your existing implementation)
from market_agent.tools.google_search import (
    google_search
)

# ------------------------------------------------------------
# Market Intelligence Agent
# ------------------------------------------------------------
market_intelligence_agent = LlmAgent(
    name="market_intelligence_agent",

    # Shown in ADK UI + high-level context
    description=DESCRIPTION,

    # This is the SYSTEM PROMPT (rules + reasoning behavior)
    instruction=INSTRUCTIONS,

    # Tools available to the LLM
    tools=[
        google_search,                 # External market trends
        get_cloud_security_performance # Internal sales analytics
    ]
)


root_agent = market_intelligence_agent
