from datetime import date, timedelta
from typing import Optional, List
from google.cloud import bigquery
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

# ================================================================
# PRODUCTS TABLE CRUD (DIMENSION)
# ================================================================

def create_product(product_id: str, product_name: str, category: str) -> str:
    """
    Create a new product entry.
    """
    query = f"""
    INSERT INTO `{BQ_PROJECT_ID}.{BQ_DATASET}.products`
    (product_id, product_name, category)
    VALUES ('{product_id}', '{product_name}', '{category}')
    """
    client.query(query).result()
    return "Product created successfully."


def read_products(category: Optional[str] = None) -> List[dict]:
    """
    Read products, optionally filtered by category.
    """
    condition = f"WHERE category = '{category}'" if category else ""
    query = f"""
    SELECT * FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.products`
    {condition}
    ORDER BY product_name
    """
    return list(client.query(query))


def update_product(
    product_id: str,
    product_name: Optional[str] = None,
    category: Optional[str] = None
) -> str:
    """
    Update product attributes.
    """
    updates = []
    if product_name:
        updates.append(f"product_name = '{product_name}'")
    if category:
        updates.append(f"category = '{category}'")

    if not updates:
        return "No fields provided for update."

    query = f"""
    UPDATE `{BQ_PROJECT_ID}.{BQ_DATASET}.products`
    SET {", ".join(updates)}
    WHERE product_id = '{product_id}'
    """
    client.query(query).result()
    return "Product updated successfully."


def delete_product(product_id: str) -> str:
    """
    Delete a product by ID.
    """
    query = f"""
    DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.products`
    WHERE product_id = '{product_id}'
    """
    client.query(query).result()
    return "Product deleted successfully."

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
    query = f"""
    INSERT INTO `{BQ_PROJECT_ID}.{BQ_DATASET}.sales`
    (sale_id, product_id, sale_date, revenue)
    VALUES ('{sale_id}', '{product_id}', DATE('{sale_date}'), {revenue})
    """
    client.query(query).result()
    return "Sale created successfully."


def read_sales(
    product_id: Optional[str] = None,
    start_date: Optional[str] = None
) -> List[dict]:
    """
    Read sales records with optional product and date filtering.
    """
    conditions = []
    if product_id:
        conditions.append(f"product_id = '{product_id}'")
    if start_date:
        conditions.append(f"sale_date >= DATE('{start_date}')")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
    SELECT * FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.sales`
    {where_clause}
    ORDER BY sale_date DESC
    """
    return list(client.query(query))


def update_sale(sale_id: str, revenue: float) -> str:
    """
    Update revenue for a sale.
    """
    query = f"""
    UPDATE `{BQ_PROJECT_ID}.{BQ_DATASET}.sales`
    SET revenue = {revenue}
    WHERE sale_id = '{sale_id}'
    """
    client.query(query).result()
    return "Sale updated successfully."


def delete_sale(sale_id: str) -> str:
    """
    Delete a sale record.
    """
    query = f"""
    DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.sales`
    WHERE sale_id = '{sale_id}'
    """
    client.query(query).result()
    return "Sale deleted successfully."

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
    query = f"""
    INSERT INTO `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
    (report_date, category, growth_percent, source)
    VALUES (DATE('{report_date}'), '{category}', {growth_percent}, '{source}')
    """
    client.query(query).result()
    return "Market growth record created successfully."


def read_market_growth(category: Optional[str] = None) -> List[dict]:
    """
    Read market growth data, optionally filtered by category.
    """
    condition = f"WHERE category = '{category}'" if category else ""
    query = f"""
    SELECT * FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
    {condition}
    ORDER BY report_date DESC
    """
    return list(client.query(query))


def update_market_growth(
    report_date: str,
    category: str,
    growth_percent: float
) -> str:
    """
    Update market growth percentage.
    """
    query = f"""
    UPDATE `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
    SET growth_percent = {growth_percent}
    WHERE report_date = DATE('{report_date}')
      AND category = '{category}'
    """
    client.query(query).result()
    return "Market growth record updated successfully."


def delete_market_growth(report_date: str, category: str) -> str:
    """
    Delete a market growth record.
    """
    query = f"""
    DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
    WHERE report_date = DATE('{report_date}')
      AND category = '{category}'
    """
    client.query(query).result()
    return "Market growth record deleted successfully."

# ================================================================
# ANALYTICAL QUERY (USED BY LLM AGENT)
# ================================================================

def get_cloud_security_performance(days_back: int = 30) -> List[dict]:
    """
    Compare internal Cloud Security sales performance against
    the latest available market growth benchmark.
    """
    start_date = date.today() - timedelta(days=days_back)

    query = f"""
    WITH latest_market_growth AS (
      SELECT
        category,
        growth_percent
      FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
      WHERE category = 'Cloud Security'
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
    WHERE p.category = 'Cloud Security'
      AND s.sale_date >= DATE('{start_date}')
    GROUP BY lmg.growth_percent
    """

    return list(client.query(query))



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






# (venv) D:\Agent-Development-Kit\adk08>uv run python -m market_agent.tools.bigquery_tool2
# === BigQuery Tool Smoke Test ===
# Traceback (most recent call last):
#   File "<frozen runpy>", line 198, in _run_module_as_main
#   File "<frozen runpy>", line 88, in _run_code
#   File "D:\Agent-Development-Kit\adk08\market_agent\tools\bigquery_tool2.py", line 269, in <module>
#     print(create_product("P100", "Cloud Shield", "Cloud Security"))
#           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "D:\Agent-Development-Kit\adk08\market_agent\tools\bigquery_tool2.py", line 37, in create_product
#     client.query(query).result()
#   File "D:\Agent-Development-Kit\venv\Lib\site-packages\google\cloud\bigquery\job\query.py", line 1773, in result
#     while not is_job_done():
#               ^^^^^^^^^^^^^
#   File "D:\Agent-Development-Kit\venv\Lib\site-packages\google\api_core\retry\retry_unary.py", line 294, in retry_wrapped_func
#     return retry_target(
#            ^^^^^^^^^^^^^
#   File "D:\Agent-Development-Kit\venv\Lib\site-packages\google\api_core\retry\retry_unary.py", line 156, in retry_target
#     next_sleep = _retry_error_helper(
#                  ^^^^^^^^^^^^^^^^^^^^
#   File "D:\Agent-Development-Kit\venv\Lib\site-packages\google\api_core\retry\retry_base.py", line 214, in _retry_error_helper
#     raise final_exc from source_exc
#   File "D:\Agent-Development-Kit\venv\Lib\site-packages\google\api_core\retry\retry_unary.py", line 147, in retry_target
#     result = target()
#              ^^^^^^^^
#   File "D:\Agent-Development-Kit\venv\Lib\site-packages\google\cloud\bigquery\job\query.py", line 1722, in is_job_done
#     raise job_failed_exception
# google.api_core.exceptions.Forbidden: 403 Billing has not been enabled for this project. Enable billing at https://console.cloud.google.com/billing. DML queries are not allowed in the free tier. Set up a billing account to remove this restriction.; reason: billingNotEnabled, message: Billing has not been enabled for this project. Enable billing at https://console.cloud.google.com/billing. DML queries are not allowed in the free tier. Set up a billing account to remove this restriction.

# Location: US
# Job ID: 6832398b-4f31-42ec-a1d9-3d7e23fff694
