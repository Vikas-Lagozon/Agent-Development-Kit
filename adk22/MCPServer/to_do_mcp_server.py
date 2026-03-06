import asyncio
import json
import os
import sys
import logging
from typing import Any, Dict, List, Optional

# --- MCP Server Imports ---
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# --- ADK Imports ---
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

# --- Database Imports ---
import aiosqlite

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("todo_tracker_server")

DB_PATH = os.path.join(os.path.dirname(__file__), "todo.db")
_db_initialized = False

app = Server("ToDoTracker-ADK-MCP")

# ---------------------------
# Database Logic
# ---------------------------

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority TEXT DEFAULT 'medium',
                due_date TEXT DEFAULT '',
                status TEXT DEFAULT 'pending'
            )
        """)
        await db.commit()


async def _ensure_db() -> None:
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True
        logger.info("Database initialized.")


# ---------------------------
# Tool Functions
# ---------------------------

async def add_task_tool(
    title: str,
    description: str = '',
    priority: str = 'medium',
    due_date: str = ''
) -> Dict[str, Any]:
    """Add a new task."""
    
    await _ensure_db()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO tasks (title, description, priority, due_date)
            VALUES (?, ?, ?, ?)
            """,
            (title, description, priority, due_date)
        )
        await db.commit()

        return {"status": "ok", "task_id": cursor.lastrowid}


async def edit_task_tool(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """Update an existing task."""

    await _ensure_db()

    updates = []
    params = []

    if title:
        updates.append("title = ?")
        params.append(title)

    if description is not None:
        updates.append("description = ?")
        params.append(description)

    if priority:
        updates.append("priority = ?")
        params.append(priority)

    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date)

    if status:
        updates.append("status = ?")
        params.append(status)

    if not updates:
        return {"status": "error", "message": "No fields to update"}

    params.append(task_id)

    async with aiosqlite.connect(DB_PATH) as db:
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        cursor = await db.execute(query, params)
        await db.commit()

        if cursor.rowcount == 0:
            return {"status": "error", "message": "Task not found"}

        return {"status": "ok", "message": f"Task {task_id} updated"}


async def delete_task_tool(task_id: int) -> Dict[str, Any]:
    """Delete a task by ID."""

    await _ensure_db()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )
        await db.commit()

        if cursor.rowcount == 0:
            return {"status": "error", "message": "Task not found"}

        return {"status": "ok", "message": f"Task {task_id} deleted"}


async def complete_task_tool(task_id: int) -> Dict[str, Any]:
    """Mark task as completed."""

    await _ensure_db()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE tasks SET status = 'completed' WHERE id = ?",
            (task_id,)
        )
        await db.commit()

        if cursor.rowcount == 0:
            return {"status": "error", "message": "Task not found"}

        return {"status": "ok", "message": f"Task {task_id} marked completed"}


async def search_tasks_tool(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search tasks using filters."""

    await _ensure_db()

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        query = "SELECT * FROM tasks"
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if priority:
            conditions.append("priority = ?")
            params.append(priority)

        if due_date:
            conditions.append("due_date = ?")
            params.append(due_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        return [dict(row) for row in rows]


# ---------------------------
# Wrap Tools
# ---------------------------

adk_tools = [
    FunctionTool(add_task_tool),
    FunctionTool(edit_task_tool),
    FunctionTool(delete_task_tool),
    FunctionTool(complete_task_tool),
    FunctionTool(search_tasks_tool),
]


# ---------------------------
# MCP Tool Listing
# ---------------------------

@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    logger.info("MCP: list_tools requested")
    return [adk_to_mcp_tool_type(tool) for tool in adk_tools]


# ---------------------------
# MCP Tool Call Handler
# ---------------------------

@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:

    logger.info(f"MCP: call_tool '{name}'")

    tool = next((t for t in adk_tools if t.name == name), None)

    if not tool:
        return [mcp_types.TextContent(type="text", text=json.dumps({"error": "Tool not found"}))]

    try:

        result = await tool.run_async(
            args=arguments,
            tool_context=None
        )

        return [
            mcp_types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )
        ]

    except Exception as e:

        logger.error(f"Error in {name}: {e}")

        return [
            mcp_types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)})
            )
        ]


# ---------------------------
# Run MCP Server
# ---------------------------

async def run_mcp_stdio_server():

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):

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
    asyncio.run(run_mcp_stdio_server())
