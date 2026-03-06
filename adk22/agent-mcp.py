import os
import sys
import certifi
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from .config import config

# -----------------------------
# Setup API Key and model
# -----------------------------
MODEL = config.MODEL
# Use sys.executable to ensure we use the SAME venv
PATH_TO_PYTHON = sys.executable 

google_api_key = config.GOOGLE_API_KEY.strip()
os.environ["GOOGLE_API_KEY"] = google_api_key

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# -----------------------------
# Path to your MCP server script
# -----------------------------
# Ensure this path is correct for your local setup
PATH_TO_YOUR_MCP_SERVER_SCRIPT = r"D:\Agent-Development-Kit\adk22\MCPServer\my_adk_mcp_server.py"

# -----------------------------
# Setup MCP Toolset for the agent
# -----------------------------
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            # FIX: Added "-u" for unbuffered output
            args=["-u", PATH_TO_YOUR_MCP_SERVER_SCRIPT], 
            cwd=r"D:\Agent-Development-Kit\adk22\MCPServer"
        ),
        # Increased timeout just in case Windows is being slow
        timeout_in_seconds=30 
    ),
    tool_filter=['load_web_page'],
)

# -----------------------------
# Setup the root agent
# -----------------------------
root_agent = LlmAgent(
    model=MODEL,
    name="web_reader_mcp_client_agent",
    instruction="Use the 'load_web_page' tool to fetch content from a URL provided by the user.",
    tools=[mcp_toolset]
)

