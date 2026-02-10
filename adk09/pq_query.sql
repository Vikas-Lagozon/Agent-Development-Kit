-- pq_query.sql (no changes required)
-- ============================================================
-- Database : postgres
-- Purpose  : Market Intelligence Agent
-- Design   : Star-schema analytics (Dimension + Fact + Reference)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS market_intelligence;

CREATE TABLE IF NOT EXISTS market_intelligence.products (
    product_id      VARCHAR NOT NULL PRIMARY KEY,
    product_name    VARCHAR NOT NULL,
    category        VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS market_intelligence.sales (
    sale_id     VARCHAR NOT NULL PRIMARY KEY,
    product_id  VARCHAR NOT NULL,
    sale_date   DATE    NOT NULL,
    revenue     DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS market_intelligence.market_growth (
    report_date     DATE             NOT NULL,
    category        VARCHAR          NOT NULL,
    growth_percent  DOUBLE PRECISION NOT NULL,
    source          VARCHAR,
    PRIMARY KEY (report_date, category)
);
