# from google.adk.agents import Agent
# from google.adk.tools.mcp_tool.mcp_tool import MCPTool
# from google.adk.tools.mcp_tool.connection import StdioConnection

# # Create stdio connection
# connection = StdioConnection(
#     command="uv",
#     args=[
#         "run",
#         "python",
#         "-m",
#         "expense_tracker.server"
#     ],
# )

# # Create MCP tool
# mcp_tool = MCPTool(connection=connection)

# # Create agent
# root_agent = Agent(
#     name="assistant_agent",
#     model="qwen3:0.6b",
#     tools=[mcp_tool],
# )



# from google.adk.agents import Agent
# from google.adk.tools.mcp_tool.mcp_tool import MCPTool

# mcp_tool = MCPTool(
#     url="http://localhost:3000"
# )

# root_agent = Agent(
#     name="assistant_agent",
#     model="qwen3:0.6b",
#     tools=[mcp_tool],
# )










from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPTool

mcp_tool = MCPTool.from_command(
    command="uv",
    args=[
        "run",
        "python",
        "-m",
        "expense_tracker.server"
    ],
)

root_agent = Agent(
    name="assistant_agent",
    model="qwen3:0.6b",
    tools=[mcp_tool],
)
