"""
BigQuery Tool for Market Intelligence Database

OPTIMIZATIONS IMPLEMENTED:
1. Parameterized Queries - All queries use parameters instead of string interpolation
   - Prevents SQL injection attacks
   - Enables query plan caching in BigQuery
   - Improves security and performance

2. Query Result Caching - All SELECT queries use use_query_cache=True
   - Results are cached for up to 24 hours
   - Reduces costs for repeated queries
   - Faster response times

3. Error Handling - All insert operations check for errors
   - Returns detailed error messages
   - Better debugging and user feedback

4. Result Limits - All read operations have configurable limits (default 1000)
   - Prevents large data transfers
   - Protects against memory issues
   - Faster query execution

5. Batch Operations - Added batch insert functions
   - batch_create_products()
   - batch_create_sales()
   - batch_create_market_growth()
   - More efficient for bulk inserts

6. Partition Pruning - Enhanced date range filtering
   - Uses explicit date bounds for better partition elimination
   - Reduces data scanned in partitioned tables

7. Serialization - All query results converted to dictionaries
   - BigQuery Row objects converted to dicts for JSON serialization
   - Compatible with Pydantic and ADK framework
   - Enables proper API response formatting
"""

from datetime import date, datetime, timedelta
from typing import Optional, List
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig
from google.oauth2 import service_account
from market_agent.config import (
    BQ_PROJECT_ID,
    BQ_DATASET,
    SERVICE_ACCOUNT_FILE
)

# ================================================================
# BIGQUERY CLIENT SETUP
# ================================================================

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE
)

client = bigquery.Client(
    credentials=credentials,
    project=BQ_PROJECT_ID
)

# Default job config with query caching enabled
DEFAULT_JOB_CONFIG = QueryJobConfig(use_query_cache=True)

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def row_to_dict(row) -> dict:
    """
    Convert BigQuery Row to JSON-serializable dictionary.
    Handles date/datetime objects by converting them to ISO format strings.
    """
    result = {}
    for key, value in dict(row).items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

# ================================================================
# PRODUCTS TABLE CRUD (DIMENSION)
# ================================================================

def create_product(product_id: str, product_name: str, category: str) -> str:
    """
    Create a new product entry.
    """
    table = f"{BQ_PROJECT_ID}.{BQ_DATASET}.products"
    rows = [{
        "product_id": product_id,
        "product_name": product_name,
        "category": category
    }]
    errors = client.insert_rows_json(table, rows)
    if errors:
        return f"Product creation failed: {errors}"
    return "Product created successfully."

def batch_create_products(products: List[dict]) -> str:
    """
    Create multiple products in a single batch operation.
    Each dict should have: product_id, product_name, category
    """
    if not products:
        return "Error: No products provided for batch creation."
    
    table = f"{BQ_PROJECT_ID}.{BQ_DATASET}.products"
    errors = client.insert_rows_json(table, products)
    if errors:
        return f"Batch product creation failed: {errors}"
    return f"Successfully created {len(products)} products."

def read_products(category: Optional[str] = None, limit: int = 1000) -> List[dict]:
    """
    Read products, optionally filtered by category.
    Uses parameterized queries for security and performance.
    """
    if category:
        query = f"""
        SELECT * FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.products`
        WHERE category = @category
        ORDER BY product_name
        LIMIT @limit
        """
        job_config = QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("category", "STRING", category),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ],
            use_query_cache=True
        )
    else:
        query = f"""
        SELECT * FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.products`
        ORDER BY product_name
        LIMIT @limit
        """
        job_config = QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ],
            use_query_cache=True
        )
    
    return [row_to_dict(row) for row in client.query(query, job_config=job_config)]

def update_product(product_id: str, product_name: Optional[str] = None, category: Optional[str] = None) -> str:
    """
    Update product attributes using parameterized queries.
    """
    updates = []
    params = [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)]
    
    if product_name:
        updates.append("product_name = @product_name")
        params.append(bigquery.ScalarQueryParameter("product_name", "STRING", product_name))
    if category:
        updates.append("category = @category")
        params.append(bigquery.ScalarQueryParameter("category", "STRING", category))

    if not updates:
        return "No fields provided for update."

    query = f"""
    UPDATE `{BQ_PROJECT_ID}.{BQ_DATASET}.products`
    SET {", ".join(updates)}
    WHERE product_id = @product_id
    """
    job_config = QueryJobConfig(query_parameters=params)
    client.query(query, job_config=job_config).result()
    return "Product updated successfully."

def delete_product(product_id: str) -> str:
    """
    Delete a product by ID using parameterized query.
    """
    query = f"""
    DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.products`
    WHERE product_id = @product_id
    """
    job_config = QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id)
        ]
    )
    client.query(query, job_config=job_config).result()
    return "Product deleted successfully."

def product_tool(operation: str, product_id: Optional[str] = None, product_name: Optional[str] = None, category: Optional[str] = None, limit: int = 1000) -> str:
    """
    Unified tool for managing products in the database.
    
    The LLM should specify one of the following operations:
      - "create" or "add"     → requires product_id, product_name, category
      - "read" or "list"      → optional category filter, limit (default 1000)
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
            return read_products(category=category, limit=limit)
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
# SALES TABLE CRUD (FACT)
# ================================================================

def create_sale(
    sale_id: str,
    product_id: str,
    sale_date: str,
    revenue: float
) -> str:
    """
    Create a new sales record.
    """
    table = f"{BQ_PROJECT_ID}.{BQ_DATASET}.sales"
    rows = [{
        "sale_id": sale_id,
        "product_id": product_id,
        "sale_date": sale_date,
        "revenue": revenue
    }]
    errors = client.insert_rows_json(table, rows)
    if errors:
        return f"Sale creation failed: {errors}"
    return "Sale created successfully."

def batch_create_sales(sales: List[dict]) -> str:
    """
    Create multiple sales in a single batch operation.
    Each dict should have: sale_id, product_id, sale_date, revenue
    """
    if not sales:
        return "Error: No sales provided for batch creation."
    
    table = f"{BQ_PROJECT_ID}.{BQ_DATASET}.sales"
    errors = client.insert_rows_json(table, sales)
    if errors:
        return f"Batch sale creation failed: {errors}"
    return f"Successfully created {len(sales)} sales."

def read_sales(
    product_id: Optional[str] = None,
    start_date: Optional[str] = None,
    limit: int = 1000
) -> List[dict]:
    """
    Read sales records with optional product and date filtering.
    Uses parameterized queries for security and performance.
    """
    params = [bigquery.ScalarQueryParameter("limit", "INT64", limit)]
    conditions = []
    
    if product_id:
        conditions.append("product_id = @product_id")
        params.append(bigquery.ScalarQueryParameter("product_id", "STRING", product_id))
    if start_date:
        conditions.append("sale_date >= @start_date")
        params.append(bigquery.ScalarQueryParameter("start_date", "DATE", start_date))

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
    SELECT * FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.sales`
    {where_clause}
    ORDER BY sale_date DESC
    LIMIT @limit
    """
    job_config = QueryJobConfig(query_parameters=params, use_query_cache=True)
    return [row_to_dict(row) for row in client.query(query, job_config=job_config)]

def update_sale(sale_id: str, product_id: Optional[str] = None, sale_date: Optional[str] = None, revenue: Optional[float] = None) -> str:
    """
    Update sale attributes using parameterized queries.
    """
    updates = []
    params = [bigquery.ScalarQueryParameter("sale_id", "STRING", sale_id)]
    
    if product_id:
        updates.append("product_id = @product_id")
        params.append(bigquery.ScalarQueryParameter("product_id", "STRING", product_id))
    if sale_date:
        updates.append("sale_date = @sale_date")
        params.append(bigquery.ScalarQueryParameter("sale_date", "DATE", sale_date))
    if revenue is not None:
        updates.append("revenue = @revenue")
        params.append(bigquery.ScalarQueryParameter("revenue", "FLOAT64", revenue))

    if not updates:
        return "No fields provided for update."

    query = f"""
    UPDATE `{BQ_PROJECT_ID}.{BQ_DATASET}.sales`
    SET {", ".join(updates)}
    WHERE sale_id = @sale_id
    """
    job_config = QueryJobConfig(query_parameters=params)
    client.query(query, job_config=job_config).result()
    return "Sale updated successfully."

def delete_sale(sale_id: str) -> str:
    """
    Delete a sale record using parameterized query.
    """
    query = f"""
    DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.sales`
    WHERE sale_id = @sale_id
    """
    job_config = QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("sale_id", "STRING", sale_id)
        ]
    )
    client.query(query, job_config=job_config).result()
    return "Sale deleted successfully."

def sale_tool(operation: str, sale_id: Optional[str] = None, product_id: Optional[str] = None, sale_date: Optional[str] = None, revenue: Optional[float] = None, start_date: Optional[str] = None, limit: int = 1000) -> str:
    """
    Unified tool for managing sales records in the database.
    
    The LLM should specify one of the following operations:
      - "create" or "add"       → requires sale_id, product_id, sale_date, revenue
      - "read" or "list"        → optional product_id and/or start_date filters, limit (default 1000)
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
            return read_sales(product_id=product_id, start_date=start_date, limit=limit)
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
# MARKET GROWTH TABLE CRUD (REFERENCE)
# ================================================================

def create_market_growth(
    report_date: str,
    category: str,
    growth_percent: float,
    source: str
) -> str:
    """
    Insert a market growth report.
    """
    table = f"{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth"
    rows = [{
        "report_date": report_date,
        "category": category,
        "growth_percent": growth_percent,
        "source": source
    }]
    errors = client.insert_rows_json(table, rows)
    if errors:
        return f"Market growth record creation failed: {errors}"
    return "Market growth record created successfully."

def batch_create_market_growth(records: List[dict]) -> str:
    """
    Create multiple market growth records in a single batch operation.
    Each dict should have: report_date, category, growth_percent, source
    """
    if not records:
        return "Error: No market growth records provided for batch creation."
    
    table = f"{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth"
    errors = client.insert_rows_json(table, records)
    if errors:
        return f"Batch market growth creation failed: {errors}"
    return f"Successfully created {len(records)} market growth records."

def read_market_growth(category: Optional[str] = None, limit: int = 1000) -> List[dict]:
    """
    Read market growth data, optionally filtered by category.
    Uses parameterized queries for security and performance.
    """
    if category:
        query = f"""
        SELECT * FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
        WHERE category = @category
        ORDER BY report_date DESC
        LIMIT @limit
        """
        job_config = QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("category", "STRING", category),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ],
            use_query_cache=True
        )
    else:
        query = f"""
        SELECT * FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
        ORDER BY report_date DESC
        LIMIT @limit
        """
        job_config = QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ],
            use_query_cache=True
        )
    
    return [row_to_dict(row) for row in client.query(query, job_config=job_config)]

def update_market_growth(
    report_date: str,
    category: str,
    growth_percent: float
) -> str:
    """
    Update market growth percentage using parameterized queries.
    """
    query = f"""
    UPDATE `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
    SET growth_percent = @growth_percent
    WHERE report_date = @report_date
      AND category = @category
    """
    job_config = QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("growth_percent", "FLOAT64", growth_percent),
            bigquery.ScalarQueryParameter("report_date", "DATE", report_date),
            bigquery.ScalarQueryParameter("category", "STRING", category)
        ]
    )
    client.query(query, job_config=job_config).result()
    return "Market growth record updated successfully."

def delete_market_growth(report_date: str, category: str) -> str:
    """
    Delete a market growth record using parameterized query.
    """
    query = f"""
    DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
    WHERE report_date = @report_date
      AND category = @category
    """
    job_config = QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("report_date", "DATE", report_date),
            bigquery.ScalarQueryParameter("category", "STRING", category)
        ]
    )
    client.query(query, job_config=job_config).result()
    return "Market growth record deleted successfully."

def market_growth_tool(operation: str, report_date: Optional[str] = None, category: Optional[str] = None, growth_percent: Optional[float] = None, source: Optional[str] = None, limit: int = 1000) -> str:
    """
    Unified tool for managing market growth benchmark records in the database.
    
    The LLM should specify one of the following operations:
      - "create" or "add"       → requires report_date, category, growth_percent, source
      - "read" or "list"        → optional category filter, limit (default 1000)
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
            return read_market_growth(category=category, limit=limit)
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
# ANALYTICAL QUERY (USED BY LLM AGENT)
# ================================================================

def get_cloud_security_performance(days_back: int = 30) -> List[dict]:
    """
    Compare internal Cloud Security sales performance against
    the latest available market growth benchmark.

    - Uses partition pruning on sales.sale_date
    - Selects the most recent market_growth record
    - Uses parameterized queries for security and performance
    """
    start_date = date.today() - timedelta(days=days_back)
    end_date = date.today()

    query = f"""
    WITH latest_market_growth AS (
      SELECT
        category,
        growth_percent
      FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
      WHERE category = @category
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY category
        ORDER BY report_date DESC
      ) = 1
    )
    SELECT
      SUM(s.revenue) AS total_revenue,
      lmg.growth_percent AS market_growth
    FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.sales` s
    JOIN `{BQ_PROJECT_ID}.{BQ_DATASET}.products` p
      ON s.product_id = p.product_id
    JOIN latest_market_growth lmg
      ON p.category = lmg.category
    WHERE p.category = @category
      AND s.sale_date >= @start_date
      AND s.sale_date < @end_date
    GROUP BY lmg.growth_percent
    """
    
    job_config = QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("category", "STRING", "Cloud Security"),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
        ],
        use_query_cache=True
    )

    return [row_to_dict(row) for row in client.query(query, job_config=job_config)]

if __name__ == "__main__":
    print("=== BigQuery Tool Smoke Test ===")

    # Test product
    print(create_product("P100", "Cloud Shield", "Cloud Security"))
    print(read_products())

    # Test sales
    print(create_sale("S100", "P100", "2026-02-01", 12000.0))
    print(read_sales(product_id="P100"))

    # Test market growth
    print(create_market_growth(
        report_date="2026-02-01",
        category="Cloud Security",
        growth_percent=14.5,
        source="Manual Test"
    ))
    print(read_market_growth("Cloud Security"))

    # Test analytics
    print(get_cloud_security_performance(days_back=60))
