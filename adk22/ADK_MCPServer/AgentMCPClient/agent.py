import os
import sys
import certifi
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from .config import config

# SSL Fixes
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

PATH_TO_PYTHON = sys.executable
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

# -----------------------------
# 1. Web Reader MCP Toolset
# -----------------------------
web_reader_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=["-u", r"D:\Agent-Development-Kit\adk22\MCPServer\my_adk_mcp_server.py"],
            cwd=r"D:\Agent-Development-Kit\adk22\MCPServer"
        ),
        timeout_in_seconds=30
    )
)

# -----------------------------
# 2. Expense Tracker MCP Toolset
# -----------------------------
expense_tracker_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=["-u", r"D:\Agent-Development-Kit\adk22\MCPServer\expense_tracker_mcp_server.py"],
            cwd=r"D:\Agent-Development-Kit\adk22\MCPServer"
        ),
        timeout_in_seconds=30
    )
)

# -----------------------------
# 3. To Do MCP Toolset
# -----------------------------
to_do_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=["-u", r"D:\Agent-Development-Kit\adk22\MCPServer\to_do_mcp_server.py"],
            cwd=r"D:\Agent-Development-Kit\adk22\MCPServer"
        ),
        timeout_in_seconds=30
    )
)

# -----------------------------
# Root Agent with BOTH Toolsets
# -----------------------------
root_agent = LlmAgent(
    model=config.MODEL,
    name="financial_assistant_agent",
    instruction=(
        "You are a helpful assistant. You can browse the web using the web_reader tools "
        "and manage expenses using the expense_tracker tools. "
        "When recording an expense, ensure you ask for the date, amount, and category if missing."
    ),
    tools=[web_reader_mcp, expense_tracker_mcp, to_do_mcp]
)
