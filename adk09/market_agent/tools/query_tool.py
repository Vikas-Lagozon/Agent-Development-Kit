# query_tool.py
from datetime import date, timedelta
from typing import Optional, List, Dict, Any, Union
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from market_agent.config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DB_SCHEMA,
)

@contextmanager
def get_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        options=f"-c search_path={DB_SCHEMA}"
    )
    try:
        yield conn
    finally:
        conn.close()

# ================================================================
# PRODUCTS TABLE CRUD
# ================================================================

def create_product(product_id: str, product_name: str, category: str) -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO products (product_id, product_name, category)
                VALUES (%s, %s, %s)
            """, (product_id, product_name, category))
            conn.commit()
    return "Product created successfully."


def read_products(category: Optional[str] = None) -> List[Dict[str, Any]]:
    if category:
        query = "SELECT * FROM products WHERE category = %s ORDER BY product_name"
        params = (category,)
    else:
        query = "SELECT * FROM products ORDER BY product_name"
        params = ()

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def update_product(product_id: str, product_name: Optional[str] = None, category: Optional[str] = None) -> str:
    updates = []
    params = []
    if product_name is not None:
        updates.append("product_name = %s")
        params.append(product_name)
    if category is not None:
        updates.append("category = %s")
        params.append(category)

    if not updates:
        return "No fields provided for update."

    query = f"UPDATE products SET {', '.join(updates)} WHERE product_id = %s"
    params.append(product_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    return "Product updated successfully."


def delete_product(product_id: str) -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
            conn.commit()
    return "Product deleted successfully."


def product_tool(
    operation: str,
    product_id: Optional[str] = None,
    product_name: Optional[str] = None,
    category: Optional[str] = None
) -> Any:
    """
    Unified tool for managing products in the database.
    
    The LLM should specify one of the following operations:
      - "create" or "add"     → requires product_id, product_name, category
      - "read" or "list"      → optional category filter
      - "update" or "edit"    → requires product_id, at least one of product_name or category
      - "delete" or "remove"  → requires product_id
    
    Returns:
        - For create/update/delete: str message (success or error)
        - For read/list: List[Dict] of products or empty list
    """
    if not operation:
        return "Error: 'operation' parameter is required. Use: create, read, update, delete"

    op = operation.lower().strip()

    # ── CREATE ───────────────────────────────────────────────────────────────
    if op in ("create", "add", "create product", "add product"):
        if not all([product_id, product_name, category]):
            return "Error: For create/add, all of product_id, product_name, category are required."
        
        try:
            return create_product(product_id, product_name, category)
        except Exception as e:
            return f"Create failed: {str(e)}"

    # ── READ / LIST ──────────────────────────────────────────────────────────
    elif op in ("read", "list", "read products", "list products"):
        try:
            return read_products(category=category)
        except Exception as e:
            return [{"error": f"Read failed: {str(e)}"}]

    # ── UPDATE ───────────────────────────────────────────────────────────────
    elif op in ("update", "edit", "update product"):
        if not product_id:
            return "Error: product_id is required for update."
        if product_name is None and category is None:
            return "Error: At least one of product_name or category must be provided for update."
        
        try:
            return update_product(product_id, product_name, category)
        except Exception as e:
            return f"Update failed: {str(e)}"

    # ── DELETE ───────────────────────────────────────────────────────────────
    elif op in ("delete", "remove", "delete product"):
        if not product_id:
            return "Error: product_id is required for delete."
        
        try:
            return delete_product(product_id)
        except Exception as e:
            return f"Delete failed: {str(e)}"

    # ── Unknown operation ────────────────────────────────────────────────────
    else:
        return (
            f"Error: Unknown operation '{operation}'. "
            "Supported operations: create, read, update, delete"
        )

    


# ================================================================
# SALES TABLE CRUD
# ================================================================

def create_sale(
    sale_id: str,
    product_id: str,
    sale_date: str,
    revenue: float
) -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sales (sale_id, product_id, sale_date, revenue)
                VALUES (%s, %s, %s, %s)
            """, (sale_id, product_id, sale_date, revenue))
            conn.commit()
    return "Sale created successfully."


def read_sales(
    product_id: Optional[str] = None,
    start_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    conditions = []
    params = []
    if product_id:
        conditions.append("product_id = %s")
        params.append(product_id)
    if start_date:
        conditions.append("sale_date >= %s")
        params.append(start_date)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"SELECT * FROM sales{where} ORDER BY sale_date DESC"

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def update_sale(
    sale_id: str,
    product_id: Optional[str] = None,
    sale_date: Optional[str] = None,
    revenue: Optional[float] = None
) -> str:
    """
    Update one or more fields of an existing sale record.
    At least one field must be provided.
    """
    updates = []
    params = []
    
    if product_id is not None:
        updates.append("product_id = %s")
        params.append(product_id)
    if sale_date is not None:
        updates.append("sale_date = %s")
        params.append(sale_date)
    if revenue is not None:
        updates.append("revenue = %s")
        params.append(revenue)

    if not updates:
        return "No fields provided for update."

    query = f"UPDATE sales SET {', '.join(updates)} WHERE sale_id = %s"
    params.append(sale_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    return "Sale updated successfully."


def delete_sale(sale_id: str) -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sales WHERE sale_id = %s", (sale_id,))
            conn.commit()
    return "Sale deleted successfully."


def sale_tool(
    operation: str,
    sale_id: Optional[str] = None,
    product_id: Optional[str] = None,
    sale_date: Optional[str] = None,
    revenue: Optional[float] = None
) -> Any:
    """
    Unified tool for managing sales records in the database.
    
    The LLM should specify one of the following operations:
      - "create" or "add"       → requires sale_id, product_id, sale_date, revenue
      - "read" or "list"        → optional product_id and/or start_date filters
      - "update" or "edit"      → requires sale_id, at least one of product_id/sale_date/revenue
      - "delete" or "remove"    → requires sale_id
    
    Returns:
        - For create/update/delete: str message (success or error)
        - For read/list: List[Dict] of sales records or empty list
    """
    if not operation:
        return "Error: 'operation' parameter is required. Use: create, read, update, delete"

    op = operation.lower().strip()

    # ── CREATE ───────────────────────────────────────────────────────────────
    if op in ("create", "add", "create sale", "add sale"):
        if not all([sale_id, product_id, sale_date, revenue]):
            return "Error: For create/add, all of sale_id, product_id, sale_date, revenue are required."
        
        try:
            return create_sale(sale_id, product_id, sale_date, revenue)
        except Exception as e:
            return f"Create failed: {str(e)}"

    # ── READ / LIST ──────────────────────────────────────────────────────────
    elif op in ("read", "list", "read sales", "list sales"):
        try:
            return read_sales(product_id=product_id, start_date=sale_date)
        except Exception as e:
            return [{"error": f"Read failed: {str(e)}"}]

    # ── UPDATE ───────────────────────────────────────────────────────────────
    elif op in ("update", "edit", "update sale"):
        if not sale_id:
            return "Error: sale_id is required for update."
        if product_id is None and sale_date is None and revenue is None:
            return "Error: At least one of product_id, sale_date, or revenue must be provided for update."
        
        try:
            return update_sale(sale_id, product_id, sale_date, revenue)
        except Exception as e:
            return f"Update failed: {str(e)}"

    # ── DELETE ───────────────────────────────────────────────────────────────
    elif op in ("delete", "remove", "delete sale"):
        if not sale_id:
            return "Error: sale_id is required for delete."
        
        try:
            return delete_sale(sale_id)
        except Exception as e:
            return f"Delete failed: {str(e)}"

    # ── Unknown operation ────────────────────────────────────────────────────
    else:
        return (
            f"Error: Unknown operation '{operation}'. "
            "Supported operations: create, read, update, delete"
        )

# ================================================================
# MARKET GROWTH TABLE CRUD
# ================================================================

def create_market_growth(
    report_date: str,
    category: str,
    growth_percent: float,
    source: str
) -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO market_growth (report_date, category, growth_percent, source)
                VALUES (%s, %s, %s, %s)
            """, (report_date, category, growth_percent, source))
            conn.commit()
    return "Market growth record created successfully."


def read_market_growth(category: Optional[str] = None) -> List[Dict[str, Any]]:
    if category:
        query = "SELECT * FROM market_growth WHERE category = %s ORDER BY report_date DESC"
        params = (category,)
    else:
        query = "SELECT * FROM market_growth ORDER BY report_date DESC"
        params = ()

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def update_market_growth(
    report_date: str,
    category: str,
    growth_percent: float
) -> str:
    query = """
        UPDATE market_growth
        SET growth_percent = %s
        WHERE report_date = %s AND category = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (growth_percent, report_date, category))
            conn.commit()
    return "Market growth record updated successfully."


def delete_market_growth(report_date: str, category: str) -> str:
    query = "DELETE FROM market_growth WHERE report_date = %s AND category = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (report_date, category))
            conn.commit()
    return "Market growth record deleted successfully."


def market_growth_tool(
    operation: str,
    report_date: Optional[str] = None,
    category: Optional[str] = None,
    growth_percent: Optional[float] = None,
    source: Optional[str] = None
) -> Any:
    """
    Unified tool for managing market growth benchmark records in the database.
    
    The LLM should specify one of the following operations:
      - "create" or "add"       → requires report_date, category, growth_percent, source
      - "read" or "list"        → optional category filter
      - "update" or "edit"      → requires report_date and category, must provide growth_percent
      - "delete" or "remove"    → requires report_date and category
    
    Returns:
        - For create/update/delete: str message (success or error)
        - For read/list: List[Dict] of market growth records or empty list
    """
    if not operation:
        return "Error: 'operation' parameter is required. Use: create, read, update, delete"

    op = operation.lower().strip()

    # ── CREATE ───────────────────────────────────────────────────────────────
    if op in ("create", "add", "create market growth", "add market growth"):
        if not all([report_date, category, growth_percent is not None, source]):
            return "Error: For create/add, all of report_date, category, growth_percent, source are required."
        
        try:
            return create_market_growth(report_date, category, growth_percent, source)
        except Exception as e:
            return f"Create failed: {str(e)}"

    # ── READ / LIST ──────────────────────────────────────────────────────────
    elif op in ("read", "list", "read market growth", "list market growth"):
        try:
            return read_market_growth(category=category)
        except Exception as e:
            return [{"error": f"Read failed: {str(e)}"}]

    # ── UPDATE ───────────────────────────────────────────────────────────────
    elif op in ("update", "edit", "update market growth"):
        if not report_date or not category:
            return "Error: report_date and category are both required for update."
        if growth_percent is None:
            return "Error: growth_percent must be provided for update."
        
        try:
            return update_market_growth(report_date, category, growth_percent)
        except Exception as e:
            return f"Update failed: {str(e)}"

    # ── DELETE ───────────────────────────────────────────────────────────────
    elif op in ("delete", "remove", "delete market growth"):
        if not report_date or not category:
            return "Error: report_date and category are both required for delete."
        
        try:
            return delete_market_growth(report_date, category)
        except Exception as e:
            return f"Delete failed: {str(e)}"

    # ── Unknown operation ────────────────────────────────────────────────────
    else:
        return (
            f"Error: Unknown operation '{operation}'. "
            "Supported operations: create, read, update, delete"
        )

# ================================================================
# ANALYTICAL QUERY – used by the agent
# ================================================================

def get_cloud_security_sales_growth(days_back: Union[int, str] = 30) -> Dict[str, Any]:
    """
    Calculates internal revenue growth percentage for the 'Cloud Security' category
    over the last `days_back` days compared to the immediately preceding equal-length period.

    Returns a clean dictionary suitable for LLM consumption.

    Handles:
    - Invalid days_back → defaults to 30
    - No data → returns 0% growth with explanation
    - Database errors → returns safe error message
    - Type coercion issues → explicit conversion & validation
    """
    # ── Input validation & normalization ─────────────────────────────────────
    try:
        days = int(days_back)
        if days < 1:
            days = 30
        if days > 365 * 2:  # reasonable upper limit
            days = 365
    except (ValueError, TypeError):
        days = 30  # fallback on any conversion failure

    today = date.today()
    start_current = today - timedelta(days=days)
    start_prev    = start_current - timedelta(days=days)

    # ── SQL ──────────────────────────────────────────────────────────────────
    query = """
    SELECT
        COALESCE(
            SUM(CASE WHEN s.sale_date >= %s THEN s.revenue END),
            0
        ) AS current_revenue,

        COALESCE(
            SUM(CASE WHEN s.sale_date >= %s 
                     AND s.sale_date < %s THEN s.revenue END),
            0
        ) AS previous_revenue
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    WHERE p.category = 'Cloud Security'
      AND s.sale_date >= %s
    """

    params = (start_current, start_prev, start_current, start_prev)

    # ── Execution with safety net ────────────────────────────────────────────
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()

        # row can be None if zero rows → safe default
        if row is None:
            row = {"current_revenue": 0.0, "previous_revenue": 0.0}

        current = float(row["current_revenue"])
        previous = float(row["previous_revenue"])

    except psycopg2.Error as db_err:
        # Return safe fallback instead of crashing agent
        return {
            "status": "error",
            "message": f"Database error: {str(db_err)}",
            "internal_growth_percent": 0.0,
            "current_revenue": 0.0,
            "previous_revenue": 0.0,
            "days": days,
            "period_from": str(start_current),
            "period_to": str(today)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "internal_growth_percent": 0.0,
            "current_revenue": 0.0,
            "previous_revenue": 0.0,
            "days": days,
            "period_from": str(start_current),
            "period_to": str(today)
        }

    # ── Growth calculation ───────────────────────────────────────────────────
    if previous > 0:
        growth_pct = ((current - previous) / previous) * 100
    elif current > 0:
        growth_pct = 100.0   # grew from zero
    else:
        growth_pct = 0.0

    # ── Final clean return ───────────────────────────────────────────────────
    return {
        "status": "success",
        "internal_growth_percent": round(growth_pct, 2),
        "current_revenue": current,
        "previous_revenue": previous,
        "days_analyzed": days,
        "period_from": str(start_current),
        "period_to": str(today),
        "note": "Growth compares last {days} days vs previous {days} days" if days != 30 else None
    }

if __name__ == "__main__":
    print("=== Query Tool Smoke Test ===")
    print(create_product("P001", "Cloud Firewall Pro", "Cloud Security"))
    print(create_sale("S001", "P001", "2026-01-15", 8500.0))
    print(update_sale("S001", revenue=9500.0))
    print(read_sales(product_id="P001"))
    print(create_market_growth("2026-02-01", "Cloud Security", 12.8, "Gartner"))
    print(get_cloud_security_sales_growth(45))
