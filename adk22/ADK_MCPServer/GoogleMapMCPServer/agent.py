# agent.py
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from .config import config

# -----------------------------
# Setup API Key and model
# -----------------------------
APP_NAME = "chatbot_google_map"
USER_ID = "user_001"
SESSION_ID = "session_001"
MODEL = config.MODEL

google_maps_api_key = config.GOOGLE_MAPS_API_KEY.strip()
google_api_key = config.GOOGLE_API_KEY.strip()

# set environment variables
os.environ["GOOGLE_API_KEY"] = google_api_key
os.environ["GOOGLE_MAPS_API_KEY"] = google_maps_api_key

# -----------------------------
# Create the root agent
# -----------------------------
root_agent = LlmAgent(
    model=MODEL,
    name="maps_assistant_agent",
    instruction="Help the user with mapping directions, and finding places using Google Map tools.",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-google-maps"],
                    env={"GOOGLE_MAPS_API_KEY": google_maps_api_key}
                ),
            ),
            # tool_filter=[
            #     'get_directions',
            #     'find_place_by_id',
            #     'find_places',
            #     'geocode_address',
            #     'reverse_geocode',
            #     'get_place_details',
            #     'get_elevation',
            #     'calculate_distance',
            # ]
        )
    ],
)

