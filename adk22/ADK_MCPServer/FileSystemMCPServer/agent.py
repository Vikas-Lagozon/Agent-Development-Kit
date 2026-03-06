import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from .config import config

# -----------------------------
# Setup API Key and model
# -----------------------------
APP_NAME = "chatbot_mcp"
USER_ID = "user_001"
SESSION_ID = "session_001"
MODEL = config.MODEL

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()

# -----------------------------
# Target folder for filesystem MCP
# -----------------------------
TARGET_FOLDER_PATH = r"D:\\Agent-Development-Kit\\adk22\ADK01_FileSystemMCPServer\\Vikas"

# -----------------------------
# Root Agent
# -----------------------------
root_agent = LlmAgent(
    model=MODEL,
    name="filesystem_assistant_agent",
    instruction="Help the user manage their files. You can list, read, write, delete and search files in the allowed directory.",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        os.path.abspath(TARGET_FOLDER_PATH),
                    ],
                ),
            ),
            tool_filter=[
                "list_directory",
                "read_file",
                "write_file",
                "delete_file",
                "search_files",
            ],
        )
    ],
)
