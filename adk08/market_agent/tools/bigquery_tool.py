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
    table = f"{BQ_PROJECT_ID}.{BQ_DATASET}.products"
    rows = [{
        "product_id": product_id,
        "product_name": product_name,
        "category": category
    }]
    client.insert_rows_json(table, rows)
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
    client.query(query)
    return "Product updated successfully."


def delete_product(product_id: str) -> str:
    """
    Delete a product by ID.
    """
    query = f"""
    DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.products`
    WHERE product_id = '{product_id}'
    """
    client.query(query)
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
    table = f"{BQ_PROJECT_ID}.{BQ_DATASET}.sales"
    rows = [{
        "sale_id": sale_id,
        "product_id": product_id,
        "sale_date": sale_date,
        "revenue": revenue
    }]
    client.insert_rows_json(table, rows)
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
    client.query(query)
    return "Sale updated successfully."


def delete_sale(sale_id: str) -> str:
    """
    Delete a sale record.
    """
    query = f"""
    DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.sales`
    WHERE sale_id = '{sale_id}'
    """
    client.query(query)
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
    table = f"{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth"
    rows = [{
        "report_date": report_date,
        "category": category,
        "growth_percent": growth_percent,
        "source": source
    }]
    client.insert_rows_json(table, rows)
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
    WHERE report_date = '{report_date}'
      AND category = '{category}'
    """
    client.query(query)
    return "Market growth record updated successfully."


def delete_market_growth(report_date: str, category: str) -> str:
    """
    Delete a market growth record.
    """
    query = f"""
    DELETE FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.market_growth`
    WHERE report_date = '{report_date}'
      AND category = '{category}'
    """
    client.query(query)
    return "Market growth record deleted successfully."

# ================================================================
# ANALYTICAL QUERY (USED BY LLM AGENT)
# ================================================================

def get_cloud_security_performance(days_back: int = 30) -> List[dict]:
    """
    Compare internal Cloud Security sales performance against
    the latest available market growth benchmark.

    - Uses partition pruning on sales.sale_date
    - Selects the most recent market_growth record
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
