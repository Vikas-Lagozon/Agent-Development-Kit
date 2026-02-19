# main.py
from fastmcp import FastMCP
import aiosqlite
import os
import json
from typing import Dict, Optional, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

_db_initialized = False

mcp = FastMCP("ExpenseTracker")


# ----------------------------
# Helpers
# ----------------------------

def success_response(tool: str, response: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": tool,
        "response": response,
    }


def error_response(tool: str, error: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "tool": tool,
        "error": error,
    }


# ----------------------------
# DB Init
# ----------------------------

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
            """
        )
        await db.commit()


async def ensure_db_exists() -> None:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO expenses (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("1970-01-01", 1, "System", "Init", "Dummy"),
        )
        await db.commit()
        await db.execute("DELETE FROM expenses WHERE id = ?", (cursor.lastrowid,))
        await db.commit()


# ----------------------------
# MCP TOOLS
# ----------------------------

@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = "",
) -> Dict[str, Any]:
    global _db_initialized
    if not _db_initialized:
        await ensure_db_exists()
        _db_initialized = True

    if amount <= 0:
        return error_response("add_expense", "Amount must be greater than zero")

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO expenses (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory, note),
        )
        await db.commit()

    return success_response(
        "add_expense",
        {
            "id": cursor.lastrowid,
            "date": date,
            "amount": amount,
            "category": category,
            "subcategory": subcategory,
            "note": note,
        },
    )


@mcp.tool()
async def edit_expense(
    expense_id: int,
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = "",
) -> Dict[str, Any]:
    if amount <= 0:
        return error_response("edit_expense", "Amount must be greater than zero")

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE expenses
            SET date = ?, amount = ?, category = ?, subcategory = ?, note = ?
            WHERE id = ?
            """,
            (date, amount, category, subcategory, note, expense_id),
        )
        await db.commit()

    if cursor.rowcount == 0:
        return error_response("edit_expense", "Expense ID not found")

    return success_response("edit_expense", {"updated": cursor.rowcount})


@mcp.tool()
async def delete_expense(expense_id: int) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM expenses WHERE id = ?", (expense_id,)
        )
        await db.commit()

    if cursor.rowcount == 0:
        return error_response("delete_expense", "Expense ID not found")

    return success_response("delete_expense", {"deleted": cursor.rowcount})


@mcp.tool()
async def list_expenses(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM expenses"
        params = []

        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params += [start_date, end_date]
        elif start_date:
            query += " WHERE date >= ?"
            params.append(start_date)
        elif end_date:
            query += " WHERE date <= ?"
            params.append(end_date)

        query += " ORDER BY date ASC"

        rows = await (await db.execute(query, params)).fetchall()

    return success_response(
        "list_expenses",
        {"count": len(rows), "expenses": [dict(r) for r in rows]},
    )


@mcp.tool()
async def summarize_expenses(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        query = "SELECT category, SUM(amount) FROM expenses"
        params, cond = [], []

        if start_date:
            cond.append("date >= ?")
            params.append(start_date)
        if end_date:
            cond.append("date <= ?")
            params.append(end_date)

        if cond:
            query += " WHERE " + " AND ".join(cond)

        query += " GROUP BY category"
        rows = await (await db.execute(query, params)).fetchall()

    summary = [{"category": r[0], "total": r[1] or 0} for r in rows]
    return success_response(
        "summarize_expenses",
        {"summary": summary, "grand_total": sum(x["total"] for x in summary)},
    )


@mcp.resource("expense://categories", mime_type="application/json")
async def categories() -> Dict[str, Any]:
    if not os.path.exists(CATEGORIES_PATH):
        return error_response("categories", "categories.json not found")

    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return success_response("categories", json.load(f))


if __name__ == "__main__":
    # STDIO MCP server (NO PORT)
    mcp.run()
