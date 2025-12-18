import sys
import subprocess
import os
import shutil
import json
import time
import requests
import socket  # Required for hostname

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# CHANGE THIS to your Server's IP
SERVER_URL = "http://10.129.141.79:5000/api/upload_scan" 

# Scan Frequency (in seconds)
# 60 = 1 minute (Testing)
# 14400 = 4 Hours (Production)
SCAN_INTERVAL = 14400 

OSQUERY_BIN = "/usr/bin/osqueryi"

# ==========================================
# 🛠️ SETUP & INSTALLATION
# ==========================================
def check_root():
    """Ensures script runs with sudo."""
    if os.geteuid() != 0:
        print("❌ ERROR: Must run as root (sudo).")
        sys.exit(1)

def install_dependencies():
    """Detects OS and installs Osquery via apt or yum."""
    if os.path.exists(OSQUERY_BIN):
        return True

    print("--- 📦 Installing Dependencies (Osquery) ---")
    
    # 1. Try APT (Debian/Ubuntu/Kali)
    try:
        subprocess.run(["which", "apt-get"], check=True, stdout=subprocess.DEVNULL)
        print(">> Detected Debian/Ubuntu.")
        
        # Add Key & Repo
        cmd_key = "export OSQUERY_KEY=1484120AC4E9F8A1A577AEEE97A80C63C9D8B80B; sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys $OSQUERY_KEY"
        subprocess.run(cmd_key, shell=True, check=True)
        
        cmd_repo = "sudo add-apt-repository 'deb [arch=amd64] https://pkg.osquery.io/deb deb main' -y"
        subprocess.run(cmd_repo, shell=True, check=True)
        
        # Install
        subprocess.run(["sudo", "apt-get", "update", "-y"], check=True)
        subprocess.run(["sudo", "apt-get", "install", "osquery", "-y"], check=True)
        return True
    except:
        pass

    # 2. Try YUM (RHEL/CentOS/Fedora)
    try:
        subprocess.run(["which", "yum"], check=True, stdout=subprocess.DEVNULL)
        print(">> Detected RHEL/CentOS.")
        subprocess.run("curl -L https://pkg.osquery.io/rpm/GPG | sudo tee /etc/pki/rpm-gpg/RPM-GPG-KEY-osquery", shell=True)
        subprocess.run("sudo yum-config-manager --add-repo https://pkg.osquery.io/rpm/osquery-s3-rpm.repo", shell=True)
        subprocess.run("sudo yum-config-manager --enable osquery-s3-rpm", shell=True)
        subprocess.run("sudo yum install osquery -y", shell=True)
        return True
    except:
        pass

    print("❌ Critical: Could not install Osquery. Is this a supported Linux distro?")
    return False

# ==========================================
# 🆔 DEVICE REGISTRATION LOGIC (NEW)
# ==========================================
def get_device_details():
    """Captures Hostname, OS, IP, and Hardware Info via Osquery."""
    device_info = {
        "hostname": socket.gethostname(),
        "ip": "unknown",
        "os": "unknown",
        "cpu": "unknown",
        "ram": "unknown"
    }

    try:
        # 1. System Info (Hostname, CPU, RAM)
        cmd_sys = [OSQUERY_BIN, "--json", "SELECT hostname, cpu_brand, physical_memory FROM system_info;"]
        res_sys = subprocess.run(cmd_sys, capture_output=True, text=True)
        if res_sys.returncode == 0:
            sys_data = json.loads(res_sys.stdout)[0]
            device_info["hostname"] = sys_data.get("hostname")
            device_info["cpu"] = sys_data.get("cpu_brand")
            # Convert bytes to GB
            ram_bytes = int(sys_data.get("physical_memory", 0))
            device_info["ram"] = f"{round(ram_bytes / 1024 / 1024 / 1024)} GB"

        # 2. OS Version
        cmd_os = [OSQUERY_BIN, "--json", "SELECT name, version, platform FROM os_version;"]
        res_os = subprocess.run(cmd_os, capture_output=True, text=True)
        if res_os.returncode == 0:
            os_data = json.loads(res_os.stdout)[0]
            device_info["os"] = f"{os_data.get('name')} {os_data.get('version')}"

        # 3. IP Address (Find first non-localhost IP)
        cmd_ip = [OSQUERY_BIN, "--json", "SELECT address FROM interface_addresses WHERE address NOT LIKE '127.%' AND address NOT LIKE '%:%';"]
        res_ip = subprocess.run(cmd_ip, capture_output=True, text=True)
        if res_ip.returncode == 0:
            ips = json.loads(res_ip.stdout)
            if ips:
                device_info["ip"] = ips[0].get("address")

    except Exception as e:
        print(f"⚠️ Error fetching device details: {e}")

    return device_info

# ==========================================
# 🕵️ ROBUST SNAP SCANNER (Hybrid Method)
# ==========================================
def get_snaps_robust():
    """
    Tries to get Snaps from Osquery (cleaner).
    If that fails or returns empty, falls back to 'snap list' command (failsafe).
    """
    inventory = []
    
    # METHOD 1: Osquery
    cmd = [OSQUERY_BIN, "--json", "SELECT name, version, revision as architecture, 'snap' as source FROM snap_packages;"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            if len(data) > 0:
                print(f"   ✅ SNAP (Osquery): Found {len(data)} packages.")
                return data
    except Exception:
        pass # Silently fail over to Method 2

    # METHOD 2: CLI Fallback
    if shutil.which("snap"):
        print("   ⚠️  Osquery missed Snaps. Falling back to 'snap list' command...")
        try:
            result = subprocess.run(["snap", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 3:
                        item = {
                            "name": parts[0],
                            "version": parts[1],
                            "architecture": parts[2],
                            "source": "snap_cli" 
                        }
                        inventory.append(item)
                print(f"   ✅ SNAP (CLI): Found {len(inventory)} packages.")
                return inventory
        except Exception as e:
            print(f"   ❌ SNAP Check Failed: {e}")
            
    return []

# ==========================================
# 🧠 MAIN SCANNING ENGINE
# ==========================================
def run_ultimate_scan():
    if not os.path.exists(OSQUERY_BIN):
        print("❌ Osquery binary missing.")
        return []

    full_inventory = []

    # 1. Standard Package Managers (Osquery Queries)
    queries = [
        {
            "type": "deb",
            "sql": "SELECT name, version, arch as architecture, 'deb' as source FROM deb_packages;"
        },
        {
            "type": "rpm",
            "sql": "SELECT name, version, arch as architecture, 'rpm' as source FROM rpm_packages;"
        },
        {
            "type": "flatpak",
            "sql": "SELECT name, version, arch as architecture, 'flatpak' as source FROM flatpak_packages;"
        },
        {
            "type": "npm",
            "sql": "SELECT name, version, 'javascript' as architecture, 'npm' as source FROM npm_packages;"
        },
        {
            "type": "pip",
            "sql": "SELECT name, version, 'python' as architecture, 'pip' as source FROM python_packages;"
        }
    ]

    print(f"🔎 Scanning Package Managers...")

    for q in queries:
        cmd = [OSQUERY_BIN, "--json", q['sql']]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                items = json.loads(res.stdout)
                if len(items) > 0:
                    print(f"   ✅ {q['type'].upper()}: Found {len(items)} packages.")
                    full_inventory.extend(items)
        except Exception:
            pass # Skip if that manager doesn't exist on this OS

    # 2. Robust Snap Check
    snap_items = get_snaps_robust()
    full_inventory.extend(snap_items)

    return full_inventory

# ==========================================
# ☁️ UPLOAD LOGIC
# ==========================================
def upload_payload(payload):
    """Sends the structured (Device + Inventory) payload."""
    try:
        # Debug info for console
        device = payload['device']
        print(f"☁️  Registering Device: {device['hostname']} ({device['ip']})")
        print(f"📦 Uploading {len(payload['inventory'])} packages to {SERVER_URL}...")
        
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(SERVER_URL, json=payload, headers=headers, timeout=20)
        
        if resp.status_code == 200:
            print("✅ Upload Success!")
        else:
            print(f"⚠️  Server returned: {resp.status_code}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

# ==========================================
# 🔄 MAIN LOOP
# ==========================================
def main():
    print("========================================")
    print("   🛡️  ULTIMATE REGISTERING AGENT")
    print("========================================")
    
    check_root()
    
    if not install_dependencies():
        print("Exiting.")
        return

    print(f"🚀 Service Started (Interval: {SCAN_INTERVAL}s)")
    
    while True:
        print(f"\n[{time.ctime()}] Starting Cycle...")
        
        # 1. Get Device Details (Registration)
        device_meta = get_device_details()
        
        # 2. Get Software Inventory
        inventory = run_ultimate_scan()
        
        # 3. Build Packet
        final_payload = {
            "device": device_meta,
            "inventory": inventory
        }

        # 4. Upload
        if inventory:
            upload_payload(final_payload)
        else:
            print("⚠️  Total inventory was empty. Nothing to upload.")
            
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()