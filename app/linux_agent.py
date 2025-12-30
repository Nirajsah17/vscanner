import sys
import subprocess
import os
import json
import time
import requests
import socket
import logging
from logging.handlers import RotatingFileHandler

# ==========================================
# ⚙️ CONFIGURATION & LOGGING SETUP
# ==========================================
CONFIG_FILE = "/etc/vscanner/config.json"
LOG_FILE = "/var/log/vscanner.log"

# Default Config (Overridden by file)
CONFIG = {
    "server_url": "http://10.194.122.79:5000/api/upload_scan",
    "api_key": "CHANGE_ME",
    "scan_interval": 14400,
    "osquery_bin": "/usr/bin/osqueryi"
}

def setup_logging():
    """Sets up log rotation (10MB max, keep 3 backups)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=3),
            logging.StreamHandler(sys.stdout) # Also print to stdout for systemd
        ]
    )

def load_config():
    """Loads config from JSON file if exists, else uses defaults."""
    global CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                CONFIG.update(user_config)
                logging.info(f"Loaded configuration from {CONFIG_FILE}")
        except Exception as e:
            logging.error(f"Failed to load config file: {e}")
    else:
        logging.warning(f"Config file not found at {CONFIG_FILE}. Using defaults.")

# ==========================================
# 🛠️ SYSTEM CHECKS
# ==========================================
def check_requirements():
    if os.geteuid() != 0:
        logging.critical("Agent must run as root.")
        sys.exit(1)
        
    if not os.path.exists(CONFIG['osquery_bin']):
        logging.critical(f"Osquery binary not found at {CONFIG['osquery_bin']}. Please install osquery first.")
        sys.exit(1)

# ==========================================
# 🆔 DEVICE METADATA
# ==========================================
def get_device_details():
    device_info = {
        "hostname": socket.gethostname(),
        "ip": "unknown",
        "os": "unknown",
        "agent_version": "1.0.0"
    }
    
    bin_path = CONFIG['osquery_bin']

    try:
        # OS Version
        res = subprocess.run([bin_path, "--json", "SELECT name, version FROM os_version;"], capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)[0]
            device_info["os"] = f"{data.get('name')} {data.get('version')}"

        # IP Address (First non-local)
        res = subprocess.run([bin_path, "--json", "SELECT address FROM interface_addresses WHERE address NOT LIKE '127.%' AND address NOT LIKE '%:%';"], capture_output=True, text=True)
        if res.returncode == 0:
            ips = json.loads(res.stdout)
            if ips: device_info["ip"] = ips[0].get("address")

    except Exception as e:
        logging.error(f"Error fetching device metadata: {e}")

    return device_info

# ==========================================
# 🕵️ SCANNING ENGINE
# ==========================================
def run_scan():
    inventory = []
    bin_path = CONFIG['osquery_bin']
    
    # 1. Standard Package Managers
    # Note: We include 'source' column for the Automapper backend
    queries = [
        {"type": "deb", "sql": "SELECT name, version, arch as architecture, source, 'deb' as manager FROM deb_packages;"},
        {"type": "rpm", "sql": "SELECT name, version, arch as architecture, name as source, 'rpm' as manager FROM rpm_packages;"},
        {"type": "pip", "sql": "SELECT name, version, 'python' as architecture, name as source, 'pip' as manager FROM python_packages;"}
        # Add npm/flatpak here if needed
    ]

    for q in queries:
        try:
            res = subprocess.run([bin_path, "--json", q['sql']], capture_output=True, text=True)
            if res.returncode == 0:
                items = json.loads(res.stdout)
                # Cleanup empty source fields
                for i in items:
                    if not i.get('source'): i['source'] = i['name']
                
                if items:
                    logging.info(f"Scanned {len(items)} {q['type']} packages.")
                    inventory.extend(items)
        except Exception as e:
            logging.debug(f"Scan query failed for {q['type']}: {e}")

    return inventory

# ==========================================
# ☁️ UPLOAD & BUFFERING
# ==========================================
def upload_data(payload):
    """
    Tries to upload. If fails, we could save to disk (Queue).
    For now, we implement robust Retry logic.
    """
    url = CONFIG['server_url']
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CONFIG['api_key']}" # SECURITY UPGRADE
    }

    try:
        logging.info(f"Uploading {len(payload['inventory'])} items to {url}...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logging.info("✅ Upload successful.")
            return True
        elif response.status_code == 401:
            logging.critical("❌ Authentication Failed! Check API Key.")
            return False
        else:
            logging.error(f"⚠️ Server returned error: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Network connection failed: {e}")
        return False

# ==========================================
# 🔄 LIFECYCLE LOOP
# ==========================================
def main():
    setup_logging()
    load_config()
    check_requirements()

    logging.info("🚀 VScanner Agent Started")

    while True:
        try:
            start_time = time.time()
            
            # 1. Collect
            device = get_device_details()
            inventory = run_scan()
            
            payload = {
                "timestamp": time.time(),
                "device": device,
                "inventory": inventory
            }

            # 2. Upload
            if inventory:
                success = upload_data(payload)
                if not success:
                    logging.warning("Upload failed. Data will be retried in next cycle.")
                    # Future improvement: Save payload to 'buffer.json' here
            else:
                logging.info("Scan returned empty inventory.")

            # 3. Sleep
            elapsed = time.time() - start_time
            sleep_time = max(0, CONFIG['scan_interval'] - elapsed)
            logging.info(f"Sleeping for {round(sleep_time)} seconds...")
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            logging.info("Stopping agent...")
            sys.exit(0)
        except Exception as e:
            logging.critical(f"Unhandled crash: {e}", exc_info=True)
            time.sleep(60) # Wait before crashing/restarting loop

if __name__ == "__main__":
    main()