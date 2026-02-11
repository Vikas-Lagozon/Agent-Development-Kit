-- ============================================================
-- DROP EXISTING TABLES
-- ============================================================

DROP TABLE IF EXISTS `modified-alloy-483408-q0.market_intelligence.sales`;
DROP TABLE IF EXISTS `modified-alloy-483408-q0.market_intelligence.products`;
DROP TABLE IF EXISTS `modified-alloy-483408-q0.market_intelligence.market_growth`;

-- ============================================================
-- RECREATE TABLES
-- ============================================================

-- PRODUCTS DIMENSION
CREATE TABLE `modified-alloy-483408-q0.market_intelligence.products`
(
  product_id STRING NOT NULL,
  product_name STRING NOT NULL,
  category STRING NOT NULL
)
CLUSTER BY category;

-- SALES FACT
CREATE TABLE `modified-alloy-483408-q0.market_intelligence.sales`
(
  sale_id STRING NOT NULL,
  product_id STRING NOT NULL,
  sale_date DATE NOT NULL,
  revenue FLOAT64 NOT NULL
)
PARTITION BY sale_date
CLUSTER BY product_id;

-- MARKET GROWTH REFERENCE
CREATE TABLE `modified-alloy-483408-q0.market_intelligence.market_growth`
(
  report_date DATE NOT NULL,
  category STRING NOT NULL,
  growth_percent FLOAT64 NOT NULL,
  source STRING
)
PARTITION BY report_date
CLUSTER BY category;

-- ============================================================
-- INSERT 20 PRODUCTS
-- ============================================================

INSERT INTO `modified-alloy-483408-q0.market_intelligence.products`
(product_id, product_name, category)
VALUES
('P01','Laptop Pro','Electronics'),
('P02','Smartphone X','Electronics'),
('P03','Tablet Air','Electronics'),
('P04','Headphones Max','Accessories'),
('P05','Smartwatch Z','Accessories'),
('P06','Gaming Console','Electronics'),
('P07','Office Chair','Furniture'),
('P08','Standing Desk','Furniture'),
('P09','LED Monitor','Electronics'),
('P10','Mechanical Keyboard','Accessories'),
('P11','Wireless Mouse','Accessories'),
('P12','Printer Pro','Electronics'),
('P13','Router Max','Electronics'),
('P14','External SSD','Electronics'),
('P15','USB Hub','Accessories'),
('P16','Webcam HD','Electronics'),
('P17','Microphone Pro','Accessories'),
('P18','Desk Lamp','Furniture'),
('P19','Bluetooth Speaker','Accessories'),
('P20','Projector 4K','Electronics');

-- ============================================================
-- INSERT 20 SALES
-- ============================================================

INSERT INTO `modified-alloy-483408-q0.market_intelligence.sales`
(sale_id, product_id, sale_date, revenue)
VALUES
('S01','P01','2025-01-01',1200),
('S02','P02','2025-01-02',900),
('S03','P03','2025-01-03',650),
('S04','P04','2025-01-04',300),
('S05','P05','2025-01-05',450),
('S06','P06','2025-01-06',800),
('S07','P07','2025-01-07',250),
('S08','P08','2025-01-08',700),
('S09','P09','2025-01-09',400),
('S10','P10','2025-01-10',150),
('S11','P11','2025-01-11',120),
('S12','P12','2025-01-12',500),
('S13','P13','2025-01-13',200),
('S14','P14','2025-01-14',180),
('S15','P15','2025-01-15',60),
('S16','P16','2025-01-16',220),
('S17','P17','2025-01-17',175),
('S18','P18','2025-01-18',90),
('S19','P19','2025-01-19',130),
('S20','P20','2025-01-20',1500);

-- ============================================================
-- INSERT 20 MARKET GROWTH RECORDS
-- ============================================================

INSERT INTO `modified-alloy-483408-q0.market_intelligence.market_growth`
(report_date, category, growth_percent, source)
VALUES
('2025-01-01','Electronics',8.5,'Gartner'),
('2025-01-01','Accessories',6.2,'IDC'),
('2025-01-01','Furniture',4.1,'Forrester'),
('2025-02-01','Electronics',9.0,'Gartner'),
('2025-02-01','Accessories',6.5,'IDC'),
('2025-02-01','Furniture',4.3,'Forrester'),
('2025-03-01','Electronics',8.8,'Gartner'),
('2025-03-01','Accessories',6.8,'IDC'),
('2025-03-01','Furniture',4.5,'Forrester'),
('2025-04-01','Electronics',9.2,'Gartner'),
('2025-04-01','Accessories',7.0,'IDC'),
('2025-04-01','Furniture',4.7,'Forrester'),
('2025-05-01','Electronics',9.5,'Gartner'),
('2025-05-01','Accessories',7.3,'IDC'),
('2025-05-01','Furniture',5.0,'Forrester'),
('2025-06-01','Electronics',9.8,'Gartner'),
('2025-06-01','Accessories',7.6,'IDC'),
('2025-06-01','Furniture',5.2,'Forrester'),
('2025-07-01','Electronics',10.0,'Gartner'),
('2025-07-01','Accessories',7.9,'IDC');

