"""
FileSystem MCP Server Entry-Point
=================================
Assembles tools from the package modules and runs the MCP server via STDIO.
BASE_DIR is resolved at connection time via config.py → .env.
IGNORED_NAMES is resolved at connection time via config.py → .env.

Run with: python file_system_mcp_server.py
"""

import asyncio
import json

# --- MCP Server Imports ---
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# --- ADK Imports ---
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

# --- Package Imports ---
from FileSystem.utils import logger, BASE_DIR, IGNORED_NAMES
from FileSystem.file_mcp import (
    read_file_tool, write_file_tool, edit_file_tool, append_file_tool,
    copy_file_tool, move_file_tool, delete_file_tool, clear_file_tool,
)
from FileSystem.directory_mcp import (
    create_directory_tool, delete_directory_tool, rename_directory_tool,
    list_files_tool, list_directories_tool, list_tree_tool,
)
from FileSystem.metadata_mcp import file_info_tool, supported_formats_tool

# from FileSystem.run_mcp import run_code

# =============================================================================
# Tool Assembly
# =============================================================================
all_tool_functions = [
    # File operations
    read_file_tool, write_file_tool, edit_file_tool, append_file_tool,
    copy_file_tool, move_file_tool, delete_file_tool, clear_file_tool,
    # Directory operations
    create_directory_tool, delete_directory_tool, rename_directory_tool,
    list_files_tool, list_directories_tool, list_tree_tool,
    # Metadata
    file_info_tool, supported_formats_tool,
    # Code execution
    # run_code,
]

adk_tools = [FunctionTool(fn) for fn in all_tool_functions]

# =============================================================================
# MCP App
# =============================================================================
app = Server("FileSystem-ADK-MCP")

# =============================================================================
# MCP Handlers
# =============================================================================

@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    logger.info("MCP list_tools called")
    return [adk_to_mcp_tool_type(t) for t in adk_tools]


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    logger.info(f"MCP call_tool: '{name}' | args: {arguments}")
    tool = next((t for t in adk_tools if t.name == name), None)
    if not tool:
        logger.warning(f"Tool not found: '{name}'")
        return [mcp_types.TextContent(type="text", text=json.dumps({"error": f"Tool not found: {name}"}))]
    try:
        result = await tool.run_async(args=arguments, tool_context=None)
        logger.info(f"Tool '{name}' completed successfully.")
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as exc:
        logger.error(f"Error executing '{name}': {exc}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]


# =============================================================================
# STDIO Server Entry-Point
# =============================================================================

async def run_mcp_stdio_server() -> None:
    logger.info(f"FileSystem MCP server starting. BASE_DIR={BASE_DIR}, IGNORED_NAMES={IGNORED_NAMES}")

    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("MCP STDIO connection established.")
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=app.name,
                    server_version="0.4.0",
                    capabilities=app.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except (RuntimeError, KeyboardInterrupt):
        logger.info("FileSystem MCP server shutting down.")
    except BaseException as exc:
        msg = str(exc).lower()
        if "cancel scope" in msg or "generatorexit" in msg:
            logger.info("FileSystem MCP server shutting down (suppressed anyio noise).")
        else:
            logger.exception("Unexpected error during server run.")
            raise


if __name__ == "__main__":
    try:
        asyncio.run(run_mcp_stdio_server())
    except (KeyboardInterrupt, SystemExit):
        pass
