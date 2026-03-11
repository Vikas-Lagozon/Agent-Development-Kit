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
logger = logging.getLogger("expense_tracker_server")

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
_db_initialized = False

app = Server("ExpenseTracker-ADK-MCP")


# --- Database Logic ---

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        await db.commit()


async def _ensure_db() -> None:
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True
        logger.info("Database initialized.")


# --- Tool Functions ---

async def add_expense_tool(date: str, amount: float, category: str, subcategory: str = '', note: str = '') -> Dict[str, Any]:
    """Adds a new expense record."""
    await _ensure_db()
    if amount <= 0:
        return {"status": "error", "error": "Amount must be > 0"}
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO expenses (date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
            (date, amount, category, subcategory, note)
        )
        await db.commit()
        return {"status": "ok", "id": cursor.lastrowid}


async def edit_expense_tool(expense_id: int, date: Optional[str] = None, amount: Optional[float] = None,
                            category: Optional[str] = None, subcategory: Optional[str] = None,
                            note: Optional[str] = None) -> Dict[str, Any]:
    """Updates an existing expense record by its ID."""
    await _ensure_db()
    updates = []
    params = []
    if date: updates.append("date = ?"); params.append(date)
    if amount: updates.append("amount = ?"); params.append(amount)
    if category: updates.append("category = ?"); params.append(category)
    if subcategory is not None: updates.append("subcategory = ?"); params.append(subcategory)
    if note is not None: updates.append("note = ?"); params.append(note)

    if not updates:
        return {"status": "error", "message": "No fields provided for update"}

    params.append(expense_id)
    async with aiosqlite.connect(DB_PATH) as db:
        query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
        cursor = await db.execute(query, params)
        await db.commit()
        if cursor.rowcount == 0:
            return {"status": "error", "message": "Expense ID not found"}
        return {"status": "ok", "message": f"Updated record {expense_id}"}


async def delete_expense_tool(expense_id: int) -> Dict[str, Any]:
    """Deletes an expense record by its ID."""
    await _ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        await db.commit()
        if cursor.rowcount == 0:
            return {"status": "error", "message": "Expense ID not found"}
        return {"status": "ok", "message": f"Deleted record {expense_id}"}


async def search_expenses_tool(category: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               min_amount: Optional[float] = None,
                               max_amount: Optional[float] = None) -> List[Dict[str, Any]]:
    """Search expenses with flexible filters (category, date range, or amount range)."""
    await _ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM expenses"
        conditions = []
        params = []

        if category:
            conditions.append("category LIKE ?")
            params.append(f"%{category}%")
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)
        if min_amount:
            conditions.append("amount >= ?")
            params.append(min_amount)
        if max_amount:
            conditions.append("amount <= ?")
            params.append(max_amount)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY date DESC"
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# --- Wrap Tools ---

adk_tools = [
    FunctionTool(add_expense_tool),
    FunctionTool(edit_expense_tool),
    FunctionTool(delete_expense_tool),
    FunctionTool(search_expenses_tool),
]


@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    logger.info("MCP: list_tools requested")
    return [adk_to_mcp_tool_type(tool) for tool in adk_tools]


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    logger.info(f"MCP: call_tool '{name}'")
    tool = next((t for t in adk_tools if t.name == name), None)
    if not tool:
        return [mcp_types.TextContent(type="text", text=json.dumps({"error": "Not found"}))]
    try:
        result = await tool.run_async(args=arguments, tool_context=None)
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return [mcp_types.TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def run_mcp_stdio_server():
    try:
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
    except (RuntimeError, KeyboardInterrupt):
        # RuntimeError covers: "Attempted to exit cancel scope in a different task"
        # This is a known anyio/mcp incompatibility on shutdown — safe to suppress.
        logger.info("Expense Tracker MCP server shutting down.")
    except BaseException as e:
        # Suppress ExceptionGroup noise from anyio TaskGroup on shutdown
        if "cancel scope" in str(e).lower() or "generatorexit" in str(e).lower():
            logger.info("Expense Tracker MCP server shutting down (suppressed anyio noise).")
        else:
            raise


if __name__ == "__main__":
    try:
        asyncio.run(run_mcp_stdio_server())
    except (KeyboardInterrupt, SystemExit):
        pass
