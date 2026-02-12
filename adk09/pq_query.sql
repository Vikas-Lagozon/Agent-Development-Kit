
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



-- Drops the entire schema including all tables, data, functions, etc.
-- DROP SCHEMA IF EXISTS market_intelligence CASCADE;










INSERT INTO market_intelligence.products (product_id, product_name, category) VALUES
('P001', 'Cloud Firewall Pro',          'Cloud Security'),
('P002', 'Secure Access Gateway',       'Cloud Security'),
('P003', 'Endpoint Threat Shield',      'Endpoint Security'),
('P004', 'Identity Access Manager',     'Identity & Access'),
('P005', 'Cloud Encryption Suite',      'Cloud Security'),
('P006', 'SIEM Cloud Edition',          'Security Analytics'),
('P007', 'Vulnerability Scanner SaaS',  'Vulnerability Mgmt'),
('P008', 'Zero Trust Network Access',   'Cloud Security'),
('P009', 'Data Loss Prevention Cloud',  'Data Security'),
('P010', 'Secure Web Gateway',          'Cloud Security'),
('P011', 'Mobile Device Manager',       'Endpoint Security'),
('P012', 'Privileged Access Manager',   'Identity & Access'),
('P013', 'Cloud WAF Enterprise',        'Cloud Security'),
('P014', 'Threat Intelligence Platform', 'Security Analytics'),
('P015', 'Container Security Scanner',  'Cloud Security'),
('P016', 'Email Security Gateway',      'Email Security'),
('P017', 'File Integrity Monitor',      'Security Analytics'),
('P018', 'API Security Protector',      'Cloud Security'),
('P019', 'Ransomware Defense Cloud',    'Endpoint Security'),
('P020', 'Compliance Automation Tool',  'Governance & Risk'),
('P021', 'Network Detection & Response','Security Analytics'),
('P022', 'Cloud Security Posture Mgmt', 'Cloud Security');



-- Realistic-looking market growth percentages
-- More frequent updates for Cloud Security
INSERT INTO market_intelligence.market_growth (report_date, category, growth_percent, source) VALUES
('2024-12-31', 'Cloud Security',          16.8,  'Gartner'),
('2025-03-31', 'Cloud Security',          17.2,  'IDC'),
('2025-06-30', 'Cloud Security',          18.1,  'MarketsandMarkets'),
('2025-09-30', 'Cloud Security',          18.9,  'Fortune Business Insights'),
('2025-12-31', 'Cloud Security',          19.4,  'Gartner 2026 Outlook'),
('2024-12-31', 'Endpoint Security',       12.5,  'IDC'),
('2025-06-30', 'Endpoint Security',       11.9,  'Gartner'),
('2025-12-31', 'Endpoint Security',       11.2,  'IDC'),
('2024-12-31', 'Identity & Access',       14.7,  'MarketsandMarkets'),
('2025-06-30', 'Identity & Access',       15.3,  'Gartner'),
('2025-12-31', 'Identity & Access',       16.1,  'Forrester'),
('2024-12-31', 'Security Analytics',      20.2,  'IDC'),
('2025-06-30', 'Security Analytics',      21.8,  'Gartner'),
('2025-12-31', 'Security Analytics',      23.4,  'MarketsandMarkets'),
('2025-03-31', 'Vulnerability Mgmt',      13.8,  'Gartner'),
('2025-09-30', 'Vulnerability Mgmt',      14.6,  'Tenable Report'),
('2025-12-31', 'Data Security',           15.9,  'IDC'),
('2025-12-31', 'Email Security',          10.4,  'Proofpoint'),
('2025-12-31', 'Governance & Risk',       12.9,  'Deloitte'),
('2026-01-31', 'Cloud Security',          19.7,  'Preliminary IDC Q1 2026');






-- Sales records mostly in late 2025 and early 2026
-- Focused more volume on Cloud Security products
INSERT INTO market_intelligence.sales (sale_id, product_id, sale_date, revenue) VALUES
('S001', 'P001', '2025-10-15',  14500.00),
('S002', 'P002', '2025-10-18',  12800.00),
('S003', 'P001', '2025-11-02',  16200.00),
('S004', 'P005', '2025-11-10',   9800.00),
('S005', 'P008', '2025-11-15',  19500.00),
('S006', 'P003', '2025-11-20',   7500.00),
('S007', 'P013', '2025-12-01',  22000.00),
('S008', 'P001', '2025-12-05',  15800.00),
('S009', 'P010', '2025-12-12',  14200.00),
('S010', 'P015', '2025-12-18',  17500.00),
('S011', 'P018', '2025-12-22',  20400.00),
('S012', 'P022', '2026-01-03',  18800.00),
('S013', 'P002', '2026-01-07',  13500.00),
('S014', 'P005', '2026-01-10',  11200.00),
('S015', 'P008', '2026-01-14',  21000.00),
('S016', 'P013', '2026-01-20',  24500.00),
('S017', 'P001', '2026-01-25',  17800.00),
('S018', 'P010', '2026-01-28',  15600.00),
('S019', 'P015', '2026-02-02',  19200.00),
('S020', 'P022', '2026-02-05',  20500.00),
('S021', 'P004', '2025-12-08',   8900.00),
('S022', 'P006', '2026-01-12',  13400.00),
('S023', 'P009', '2026-01-19',  11800.00),
('S024', 'P012', '2026-02-01',  16700.00),
('S025', 'P021', '2026-02-08',  14900.00);