import sys
import subprocess
import os
import ctypes
import urllib.request
import json
import time
import requests  # pip install requests

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
SERVER_URL = "http://192.168.1.15:5000/api/upload_scan"  # <--- CHANGE THIS IP
SCAN_INTERVAL = 14400  # 4 Hours (in seconds). Set to 60 for testing.

# Osquery Installer Config
OSQUERY_URL = "https://pkg.osquery.io/windows/osquery-5.10.2.msi"
INSTALLER_NAME = "osquery.msi"
OSQUERY_PATH = r"C:\Program Files\osquery\osqueryi.exe"

# ==========================================
# 🛠️ INSTALLATION LOGIC
# ==========================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def install_dependencies():
    """Checks if Osquery is installed. If not, downloads and installs it."""
    if os.path.exists(OSQUERY_PATH):
        return True

    print(f"--- 📦 Installing Dependencies (Osquery) ---")
    if not is_admin():
        print("❌ Admin rights required to install Osquery.")
        return False

    # 1. Download
    try:
        print(f"Downloading MSI...")
        urllib.request.urlretrieve(OSQUERY_URL, INSTALLER_NAME)
    except Exception as e:
        print(f"Download failed: {e}")
        return False

    # 2. Install (Silent)
    try:
        print("Installing... (Please wait)")
        subprocess.run(["msiexec", "/i", INSTALLER_NAME, "/quiet", "/norestart"], check=True)
        print("✅ Osquery installed successfully.")
        return True
    except subprocess.CalledProcessError:
        print("❌ Installation failed.")
        return False

# ==========================================
# 🕵️ SCANNING LOGIC
# ==========================================
def run_scan():
    """Runs Osquery to get installed programs."""
    if not os.path.exists(OSQUERY_PATH):
        print("❌ Error: Osquery binary missing.")
        return None

    query = "SELECT name, version, publisher FROM programs;"
    cmd = [OSQUERY_PATH, "--json", query]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Osquery Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Execution Error: {e}")
        return None

def upload_data(data):
    """Sends JSON payload to the Cloud Server."""
    try:
        print(f"☁️ Uploading to {SERVER_URL}...")
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(SERVER_URL, json=data, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            print("✅ Upload Success!")
        else:
            print(f"⚠️ Server returned: {resp.status_code}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

# ==========================================
# 🔄 MAIN SERVICE LOOP
# ==========================================
def main():
    print("========================================")
    print("      WINDOWS VULNERABILITY AGENT")
    print("========================================")

    # 1. Setup
    if not install_dependencies():
        print("Critical dependency missing. Exiting.")
        input("Press Enter...")
        return

    # 2. Service Loop
    print(f"🚀 Starting Service Mode (Interval: {SCAN_INTERVAL}s)")
    
    while True:
        print(f"\n[{time.ctime()}] Starting Scan Cycle...")
        
        # Scan
        inventory = run_scan()
        
        if inventory:
            print(f"found {len(inventory)} items. Uploading...")
            # Upload
            upload_data(inventory)
        
        print(f"💤 Sleeping for {SCAN_INTERVAL} seconds...")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()