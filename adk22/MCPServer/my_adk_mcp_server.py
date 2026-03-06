import asyncio
import json
import logging
import sys
from dotenv import load_dotenv

# --- Essential MCP Server Imports (Fast) ---
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# --- ADK Utility Imports ---
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

load_dotenv()

# FIX: Force logging to stderr. Stdout is reserved for JSON-RPC only.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

app = Server("adk-tool-exposing-mcp-server")

# FIX: Define the tool metadata once without importing the logic yet
# This keeps the 'list_tools' call fast.
TOOL_NAME = "load_web_page"
TOOL_DESCRIPTION = "Fetches the content of a web page given a URL."

@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """Return the tool schema. We don't need the full ADK object yet."""
    return [
        mcp_types.Tool(
            name=TOOL_NAME,
            description=TOOL_DESCRIPTION,
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch"}
                },
                "required": ["url"]
            }
        )
    ]

@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    """Execute the requested tool with 'Lazy Loading' of the ADK logic."""
    if name == TOOL_NAME:
        try:
            # FIX: Only import the heavy ADK tool when actually called
            from google.adk.tools.load_web_page import load_web_page
            from google.adk.tools.function_tool import FunctionTool
            
            logger.info(f"Executing {TOOL_NAME} for URL: {arguments.get('url')}")
            
            adk_tool = FunctionTool(load_web_page)
            adk_response = await adk_tool.run_async(
                args=arguments,
                tool_context=None,
            )
            
            return [mcp_types.TextContent(type="text", text=json.dumps(adk_response, indent=2))]

        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            return [mcp_types.TextContent(type="text", text=f"Error: {str(e)}")]

    return [mcp_types.TextContent(type="text", text=f"Tool '{name}' not found.")]

async def run_mcp_stdio_server():
    """Run the MCP server over STDIO transport."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("MCP Server stdio channel established.")
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    # Standard entry point
    asyncio.run(run_mcp_stdio_server())
