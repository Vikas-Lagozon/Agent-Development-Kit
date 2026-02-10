-- ============================================================
-- Project  : gen-lang-client-0337338794
-- Dataset  : market_intelligence
-- Purpose  : Market Intelligence Agent (Google ADK)
-- Design   : Star-schema analytics (Dimension + Fact + Reference)
-- ============================================================

-- ------------------------------------------------------------
-- DATASET
-- ------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `gen-lang-client-0337338794.market_intelligence`
OPTIONS (
  location = "US",
  description = "Market Intelligence dataset for ADK-based analytical agents"
);

-- ============================================================
-- DIMENSION TABLE: PRODUCTS
-- Defines WHAT we sell
-- ============================================================
CREATE TABLE IF NOT EXISTS
  `gen-lang-client-0337338794.market_intelligence.products`
(
  product_id STRING NOT NULL,
  product_name STRING NOT NULL,
  category STRING NOT NULL
)
CLUSTER BY category
OPTIONS (
  description = "Product dimension table. Anchor for sales and market analysis."
);

-- ============================================================
-- FACT TABLE: SALES
-- Defines HOW MUCH and WHEN we sell
-- ============================================================
CREATE TABLE IF NOT EXISTS
  `gen-lang-client-0337338794.market_intelligence.sales`
(
  sale_id STRING NOT NULL,
  product_id STRING NOT NULL,
  sale_date DATE NOT NULL,
  revenue FLOAT64 NOT NULL
)
PARTITION BY sale_date
CLUSTER BY product_id
OPTIONS (
  description = "Sales fact table. High-volume transactional data."
);

-- ============================================================
-- REFERENCE TABLE: MARKET GROWTH
-- Defines EXTERNAL MARKET BENCHMARKS
-- ============================================================
CREATE TABLE IF NOT EXISTS
  `gen-lang-client-0337338794.market_intelligence.market_growth`
(
  report_date DATE NOT NULL,
  category STRING NOT NULL,
  growth_percent FLOAT64 NOT NULL,
  source STRING
)
PARTITION BY report_date
CLUSTER BY category
OPTIONS (
  description = "External market growth reference data by category."
);

-- ============================================================
-- LOGICAL RELATIONSHIPS (DOCUMENTATION ONLY)
-- BigQuery does NOT enforce foreign keys.
-- These comments define intended joins.
-- ============================================================

-- products.product_id  = sales.product_id
-- products.category    = market_growth.category

-- JOIN FLOW USED BY AGENT:
-- sales → products → market_growth
