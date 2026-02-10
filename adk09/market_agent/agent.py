# agent.py
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from market_agent.prompt import DESCRIPTION, INSTRUCTIONS

MODEL = LiteLlm(model="ollama_chat/llama3.2:3b")

# Search tool
from market_agent.tools.search_tool import search

# Query tool
from market_agent.tools.query_tool import get_cloud_security_sales_growth, product_tool, sale_tool, market_growth_tool

# ------------------------------------------------------------
# Market Intelligence Agent
# ------------------------------------------------------------
market_intelligence_agent = LlmAgent(
    model=MODEL,
    name="market_intelligence_agent",

    # Shown in ADK UI + high-level context
    description=DESCRIPTION,

    # This is the SYSTEM PROMPT (rules + reasoning behavior)
    instruction=INSTRUCTIONS,

    # Tools available to the LLM
    tools=[
        search,                        # External market trends
        product_tool,
        sale_tool,
        market_growth_tool,
        get_cloud_security_sales_growth, # Internal sales analytics
        
    ]
)

root_agent = market_intelligence_agent
