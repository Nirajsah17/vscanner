import requests
import json
import time
import sqlite3
import datetime
from datetime import timedelta

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# Your API Key (Highly Recommended to set this to avoid rate limits)
NVD_API_KEY = None 

# Timeframe: 10 Years back
DAYS_BACK = 3650
DB_FILE = "nvd_robust.db" # Changed name to reflect new schema

# API Limits
# NIST allows 120 days max per request range
MAX_RANGE_DAYS = 120 
DELAY = 2.0 if NVD_API_KEY else 6.0

# ==========================================
# 🗄️ DATABASE SETUP (ROBUST SCHEMA)
# ==========================================
def setup_database():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Products Table (Normalization)
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor TEXT,
                    name TEXT,
                    type TEXT,
                    UNIQUE(vendor, name)
                )''')

    # 2. CVE Metadata
    c.execute('''CREATE TABLE IF NOT EXISTS cves (
                    id TEXT PRIMARY KEY,
                    description TEXT,
                    severity TEXT,
                    cvss_score REAL,
                    published_date TEXT
                )''')

    # 3. Vulnerability Rules (The Logic: Start/End Versions)
    c.execute('''CREATE TABLE IF NOT EXISTS vulnerability_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cve_id TEXT,
                    product_id INTEGER,
                    version_start TEXT,
                    version_end_excl TEXT,
                    version_end_incl TEXT,
                    FOREIGN KEY(cve_id) REFERENCES cves(id),
                    FOREIGN KEY(product_id) REFERENCES products(id)
                )''')
    
    # Indexes for performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_prod_name ON products(name)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_rules_prod ON vulnerability_rules(product_id)')
    
    conn.commit()
    return conn

# ==========================================
# 📥 DOWNLOADER LOGIC (CHUNKED)
# ==========================================
def fetch_nvd_chunk(start_date, end_date):
    """Downloads a specific 120-day window."""
    base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    headers = {"apiKey": NVD_API_KEY} if NVD_API_KEY else {}
    fmt = "%Y-%m-%dT%H:%M:%S.000"
    
    params = {
        "pubStartDate": start_date.strftime(fmt),
        "pubEndDate": end_date.strftime(fmt),
        "resultsPerPage": 2000,
        "startIndex": 0
    }

    print(f"   Downloading window: {params['pubStartDate']} -> {params['pubEndDate']}")
    
    chunk_cves = []
    
    while True:
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"   ❌ API Error {response.status_code}: {response.text}")
                time.sleep(10) 
                return []

            data = response.json()
            cves = data.get("vulnerabilities", [])
            chunk_cves.extend(cves)
            
            total_results = data.get("totalResults", 0)
            count = len(cves)
            
            if params["startIndex"] + count >= total_results or count == 0:
                break 

            params["startIndex"] += count
            time.sleep(DELAY) 

        except Exception as e:
            print(f"   ❌ Network Error: {e}")
            break

    return chunk_cves

def fetch_all_data(total_start_date, total_end_date):
    """Loops through the 10-year range in 120-day chunks."""
    all_data = []
    current_start = total_start_date
    
    print(f"--- 📡 Connecting to NVD API (Chunking 10 years) ---")
    
    while current_start < total_end_date:
        current_end = current_start + timedelta(days=MAX_RANGE_DAYS)
        if current_end > total_end_date:
            current_end = total_end_date
            
        cves = fetch_nvd_chunk(current_start, current_end)
        all_data.extend(cves)
        
        current_start = current_end
        print(f"   ✅ Chunk complete. Total collected so far: {len(all_data)}")
        
    return all_data

# ==========================================
# 💾 ROBUST PARSER & STORAGE
# ==========================================
def get_or_create_product(cursor, vendor, name, prod_type, cache):
    """Helper to handle Product Normalization efficiently."""
    key = (vendor, name)
    if key in cache:
        return cache[key]
        
    cursor.execute("INSERT OR IGNORE INTO products (vendor, name, type) VALUES (?, ?, ?)", (vendor, name, prod_type))
    
    # Get the ID (whether inserted or existed)
    if cursor.rowcount == 0:
        cursor.execute("SELECT id FROM products WHERE vendor = ? AND name = ?", (vendor, name))
        row = cursor.fetchone()
        pid = row[0] if row else None
    else:
        pid = cursor.lastrowid
        
    cache[key] = pid
    return pid

def save_to_db(conn, raw_cves):
    print(f"\n--- 💾 Saving {len(raw_cves)} records to Robust Database ---")
    c = conn.cursor()
    product_cache = {} # Local cache for this batch speedup
    count = 0
    
    for item in raw_cves:
        cve = item['cve']
        cve_id = cve['id']
        
        # --- 1. METADATA ---
        desc = "No description"
        if 'descriptions' in cve:
            for d in cve['descriptions']:
                if d['lang'] == 'en':
                    desc = d['value']
                    break
        
        score = 0.0
        severity = "UNKNOWN"
        metrics = cve.get('metrics', {})
        
        if 'cvssMetricV31' in metrics:
            m = metrics['cvssMetricV31'][0]['cvssData']
            score = m['baseScore']
            severity = m['baseSeverity']
        elif 'cvssMetricV30' in metrics:
            m = metrics['cvssMetricV30'][0]['cvssData']
            score = m['baseScore']
            severity = m['baseSeverity']
        elif 'cvssMetricV2' in metrics:
            m = metrics['cvssMetricV2'][0]['cvssData']
            score = m['baseScore']
            severity = "MEDIUM" if score < 7 else "HIGH"

        c.execute("INSERT OR REPLACE INTO cves VALUES (?, ?, ?, ?, ?)", 
                  (cve_id, desc, severity, score, cve['published']))

        # --- 2. CONFIGURATIONS (Version Ranges) ---
        if 'configurations' in cve:
            for config in cve['configurations']:
                for node in config.get('nodes', []):
                    # We only care about OR operators usually (match ANY)
                    if node.get('operator') == 'OR': 
                        for match in node.get('cpeMatch', []):
                            if match.get('vulnerable'):
                                cpe_str = match['criteria']
                                
                                # Parse CPE String: cpe:2.3:a:vendor:product:version:...
                                parts = cpe_str.split(':')
                                if len(parts) > 4:
                                    vendor = parts[3]
                                    name = parts[4]
                                    ptype = parts[2]
                                    
                                    # Normalize Product
                                    pid = get_or_create_product(c, vendor, name, ptype, product_cache)
                                    
                                    # Extract Critical Ranges
                                    v_start = match.get('versionStartIncluding')
                                    v_end_ex = match.get('versionEndExcluding')
                                    v_end_in = match.get('versionEndIncluding')
                                    
                                    # Fallback: specific version in CPE if no range
                                    if not (v_start or v_end_ex or v_end_in):
                                        specific_ver = parts[5]
                                        if specific_ver not in ('*', '-'):
                                            v_end_in = specific_ver
                                            v_start = specific_ver

                                    # Insert Rule
                                    c.execute('''INSERT INTO vulnerability_rules 
                                                 (cve_id, product_id, version_start, version_end_excl, version_end_incl)
                                                 VALUES (?, ?, ?, ?, ?)''', 
                                              (cve_id, pid, v_start, v_end_ex, v_end_in))

        count += 1
        if count % 1000 == 0:
            print(f"   Saved {count}...", end="\r")

    conn.commit()
    print(f"\n✅ Success! Robust Database ready at '{DB_FILE}'")

# ==========================================
# 🚀 MAIN
# ==========================================
if __name__ == "__main__":
    db_conn = setup_database()
    
    # Range: Now back to 10 years ago
    end = datetime.datetime.now()
    start = end - timedelta(days=DAYS_BACK)
    
    data = fetch_all_data(start, end)
    
    if data:
        save_to_db(db_conn, data)
    
    db_conn.close()