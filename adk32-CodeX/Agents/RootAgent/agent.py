# RootAgent/agent.py
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from .config import config
from .prompts import ROOT_AGENT_INSTRUCTION
from ResearchAgent.research import research_agent, get_current_datetime
from CodeXAgent.codex import codex_agent

MODEL = config.MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

PATH_TO_PYTHON = sys.executable

# ─────────────────────────────────────────────────────────────
# MCP TOOLSETS
# ─────────────────────────────────────────────────────────────
file_system_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk32-codeX\MCPServer\FileSystemMCP\file_system_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk32-codeX\MCPServer\FileSystemMCP",
        ),
        timeout_in_seconds=30,
    )
)

# ─────────────────────────────────────────────────────────────
# ROOT AGENT
# ─────────────────────────────────────────────────────────────
root_agent = LlmAgent(
    model=MODEL,
    name="root_agent",
    description="Root agent that delegates tasks to specialised sub-agents",
    instruction=ROOT_AGENT_INSTRUCTION,
    sub_agents=[
        research_agent,
        codex_agent,
    ],
    tools=[
        get_current_datetime,
        file_system_mcp,
    ],
)

