from google.adk.agents import LlmAgent
from google.adk.tools.google_search_tool import GoogleSearchTool

from market_agent.prompt import DESCRIPTION, INSTRUCTIONS
from market_agent.tools.bigquery_tool import (
    product_tool,
    sale_tool,
    market_growth_tool,
    get_cloud_security_performance,
)

# ------------------------------------------------------------
# Market Intelligence Agent
# ------------------------------------------------------------
market_intelligence_agent = LlmAgent(
    name="market_intelligence_agent",
    model="gemini-2.5-flash",
    description=DESCRIPTION,
    instruction=INSTRUCTIONS,

    tools=[
        # External research
        GoogleSearchTool(bypass_multi_tools_limit=True),
        
        # Internal data management
        product_tool,
        sale_tool,
        market_growth_tool,

        # Internal analytics
        get_cloud_security_performance,
    ],
)

root_agent = market_intelligence_agent
