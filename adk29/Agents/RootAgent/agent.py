# RootAgent/agent.py
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from .config import config

MODEL = config.MODEL
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

PATH_TO_PYTHON = sys.executable

# Import sub-agent + tool
from ResearchAgent.research import research_agent, get_current_datetime
from ProblemSolverAgent.problem_solver import problem_solver_agent
# from PythonAgent.python_code import python_agent
# from PlannerAgent.planner import planner_agent

# ─────────────────────────────────────────────────────────────
# MCP TOOLSETS
# ─────────────────────────────────────────────────────────────

# 1. Expense Tracker MCP
expense_tracker_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk29\MCPServer\expense_tracker_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk29\MCPServer",
        ),
        timeout_in_seconds=30,
    )
)

# 2. To-Do MCP
to_do_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk29\MCPServer\to_do_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk29\MCPServer",
        ),
        timeout_in_seconds=30,
    )
)

# 3. File System MCP
file_system_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=PATH_TO_PYTHON,
            args=[
                "-u",
                r"D:\Agent-Development-Kit\adk29\MCPServer\FileSystemMCP\file_system_mcp_server.py",
            ],
            cwd=r"D:\Agent-Development-Kit\adk29\MCPServer\FileSystemMCP",
        ),
        timeout_in_seconds=30,
    )
)

# ── Root LLM Agent ────────────────────────────────────────────────────────────
root_agent = LlmAgent(
    model=MODEL,
    name="root_agent",
    description="Root agent that delegates tasks to specialised remote agents",
    instruction="""
You are Jarvis, a highly capable and professional AI assistant.

You have access to the following tools and agents:

1. get_current_datetime
   - Check the current date, time, and day.

2. research_agent
   - Perform deep research and retrieve live web data.

3. expense_tracker tools
   - Record, manage, and retrieve expenses.

4. to_do tools
   - Create, update, delete, and manage tasks.

5. file_system tools
   - Read, write, list, and manage files and folders on the local file system.

6. problem_solver_agent
   - Analyse programming errors, exceptions, stack traces, bugs, and technical issues.
   - Identifies root causes via Google Search and provides step-by-step solutions.

7. python_agent
   - Applies a given solution or set of changes to a provided Python script.
   - Returns the complete updated Python script with all changes applied.

8. planner_agent
   - Creates a complete project from scratch given a project description.
   - Researches best practices, designs full directory structure, generates starter
     code for all files, physically creates the project on disk, and produces
     a detailed PROJECT.md documentation file.


DELEGATION RULES:

1. Date/Time:
   If the user asks for the current time or date, use get_current_datetime.

2. Research:
   Delegate complex research or latest news to research_agent.

3. Expense Tracking:
   Use expense_tracker tools when the user wants to add or check expenses.

4. Task Management:
   Use to_do tools when the user wants to manage tasks or reminders.

5. File System:
   Use file_system tools when the user wants to read, write, list, move,
   or delete files and folders on the local system.

6. Problem Solving — MANDATORY RULE:
   You MUST use transfer_to_agent with agent_name="problem_solver_agent" when
   the user's message contains ANY of the following:
   - An error message or exception (e.g. TypeError, ValueError, ImportError,
     NullPointerException, segmentation fault, etc.)
   - A stack trace or traceback
   - A bug description or unexpected behaviour in code
   - A configuration or environment error
   - A dependency, import, or installation problem
   - Any sentence like "I'm getting an error", "this is not working",
     "how do I fix", "why is this failing", "debug this", "solve this error"
   Do NOT try to answer the problem yourself. ALWAYS transfer to problem_solver_agent.

7. Python Script Modification — MANDATORY RULE:
   You MUST use transfer_to_agent with agent_name="python_agent" when
   the user provides a Python script AND asks you to:
   - Apply a solution, fix, or patch to it
   - Modify, update, refactor, or rewrite it
   - Add, remove, or change specific parts of the code
   - Implement a feature or improvement described in text
   The user message will typically contain a code block (```python ... ```)
   alongside instructions describing what changes to make.
   Do NOT modify the script yourself. ALWAYS transfer to python_agent.

8. Project Planning & Scaffolding — MANDATORY RULE:
   You MUST use transfer_to_agent with agent_name="planner_agent" when
   the user asks to:
   - Create a new project from scratch
   - Scaffold or bootstrap a project
   - Plan a project directory structure
   - Generate a project layout with files and folders
   - Set up a new application, service, API, or tool
   Trigger phrases: "create a project", "build a project", "scaffold",
   "plan a project", "set up a new", "create the structure for",
   "generate project files", "start a new project".
   Do NOT plan or create the project yourself. ALWAYS transfer to planner_agent.


Always:
- Maintain session context
- Provide clear structured answers
- Format responses using markdown
""",
    sub_agents=[
        research_agent,
        problem_solver_agent,
        # python_agent,
        # planner_agent,
    ],
    tools=[
        get_current_datetime,
        expense_tracker_mcp,
        to_do_mcp,
        file_system_mcp,
    ],
)

