import requests
import json
import time
import sqlite3
import datetime
from datetime import timedelta

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# Your API Key
NVD_API_KEY = None 

# Timeframe: 10 Years back
DAYS_BACK = 3650
DB_FILE = "vulnerabilities.db"

# API Limits
# NIST allows 120 days max per request range
MAX_RANGE_DAYS = 120 
DELAY = 2.0 if NVD_API_KEY else 6.0

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
def setup_database():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cves (
                    id TEXT PRIMARY KEY,
                    description TEXT,
                    severity TEXT,
                    cvss_score REAL,
                    published_date TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS cpe_matches (
                    cve_id TEXT,
                    cpe_string TEXT,
                    FOREIGN KEY(cve_id) REFERENCES cves(id)
                )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_cpe ON cpe_matches (cpe_string)')
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
                # If we hit an error, pause and retry or skip
                time.sleep(10) 
                return []

            data = response.json()
            cves = data.get("vulnerabilities", [])
            chunk_cves.extend(cves)
            
            total_results = data.get("totalResults", 0)
            count = len(cves)
            
            # Check if we got everything in this window
            if params["startIndex"] + count >= total_results or count == 0:
                break 

            # Next page within this window
            params["startIndex"] += count
            time.sleep(DELAY) # Rate limit

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
        # Calculate the end of this chunk (start + 120 days)
        current_end = current_start + timedelta(days=MAX_RANGE_DAYS)
        
        # Don't go past the present
        if current_end > total_end_date:
            current_end = total_end_date
            
        # Fetch this chunk
        cves = fetch_nvd_chunk(current_start, current_end)
        all_data.extend(cves)
        
        # Move forward
        current_start = current_end
        
        print(f"   ✅ Chunk complete. Total collected so far: {len(all_data)}")
        # Save incrementally or just keep in memory (Memory might get high for 10y)
        # Ideally, we yield here, but list extend is okay for ~200k items (approx 500MB RAM)
        
    return all_data

# ==========================================
# 💾 PARSER & STORAGE LOGIC
# ==========================================
def save_to_db(conn, raw_cves):
    print(f"\n--- 💾 Saving {len(raw_cves)} records to Database ---")
    c = conn.cursor()
    count = 0
    
    for item in raw_cves:
        cve = item['cve']
        cve_id = cve['id']
        
        # Description
        desc = "No description"
        if 'descriptions' in cve:
            for d in cve['descriptions']:
                if d['lang'] == 'en':
                    desc = d['value']
                    break
        
        # Severity
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

        try:
            c.execute("INSERT OR REPLACE INTO cves VALUES (?, ?, ?, ?, ?)", 
                      (cve_id, desc, severity, score, cve['published']))
        except sqlite3.Error:
            pass

        # CPEs
        if 'configurations' in cve:
            for config in cve['configurations']:
                for node in config.get('nodes', []):
                    for match in node.get('cpeMatch', []):
                        if match.get('vulnerable'):
                            cpe_str = match['criteria']
                            c.execute("INSERT INTO cpe_matches VALUES (?, ?)", (cve_id, cpe_str))

        count += 1
        if count % 1000 == 0:
            print(f"   Saved {count}...", end="\r")

    conn.commit()
    print(f"\n✅ Success! Database ready at '{DB_FILE}'")

# ==========================================
# 🚀 MAIN
# ==========================================
if __name__ == "__main__":
    db_conn = setup_database()
    
    # Range: Now back to 10 years ago
    end = datetime.datetime.now()
    start = end - timedelta(days=DAYS_BACK)
    
    # Fetch Loop
    # Note: This may take 30-60 minutes for 10 years of data!
    data = fetch_all_data(start, end)
    
    if data:
        save_to_db(db_conn, data)
    
    db_conn.close()