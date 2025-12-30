-- 1. CVE Metadata (Standard info)
CREATE TABLE cves (
    id TEXT PRIMARY KEY,          -- e.g., CVE-2023-44487
    description TEXT,
    severity TEXT,                -- LOW, MEDIUM, HIGH, CRITICAL
    cvss_score REAL,
    published_date TEXT,
    last_modified_date TEXT
);

-- 2. Products Table (Normalization)
-- We separate products to save space and make searching 10x faster.
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor TEXT NOT NULL,         -- e.g., 'apache'
    name TEXT NOT NULL,           -- e.g., 'http_server'
    type TEXT,                    -- 'a' (app), 'o' (os), 'h' (hardware)
    
    -- Constraint to prevent duplicate products
    UNIQUE(vendor, name)
);

-- 3. Vulnerability Rules (The Core Logic)
-- Instead of a CPE string, we store the "Range" of vulnerability.
CREATE TABLE vulnerability_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cve_id TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    
    -- The "Rule" Logic
    version_start TEXT,           -- e.g., '2.4.0'
    version_end_excl TEXT,        -- e.g., '2.4.50' (Vulnerable if < 2.4.50)
    version_end_incl TEXT,        -- e.g., '2.4.49' (Vulnerable if <= 2.4.49)
    target_sw TEXT,               -- e.g., 'linux' (Used if a product is only vuln on specific OS)
    
    FOREIGN KEY(cve_id) REFERENCES cves(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

-- Indexes (Critical for Performance)
CREATE INDEX idx_rules_product ON vulnerability_rules(product_id);
CREATE INDEX idx_products_name ON products(name);

## 2015 -> 2025