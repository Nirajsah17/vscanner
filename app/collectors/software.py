import json
import subprocess
import platform
from config import conf

OSQUERY = conf.get("osquery_bin")
OS_TYPE = platform.system()

def get_software_inventory():
    inventory = []
    queries = []

    # 1. Select Queries based on OS
    if OS_TYPE == "Windows":
        # Windows Programs + Chocolatey
        queries = [
            {"type": "win_app", "sql": "SELECT name, version, publisher as source, 'msi' as manager FROM programs;"},
            {"type": "choco", "sql": "SELECT name, version, summary as source, 'chocolatey' as manager FROM chocolatey_packages;"}
        ]
        
    elif OS_TYPE == "Darwin":
        # macOS Apps + Brew
        queries = [
            {"type": "app", "sql": "SELECT bundle_name as name, bundle_version as version, 'dmg' as manager FROM apps;"},
            {"type": "brew", "sql": "SELECT name, version, 'homebrew' as manager FROM homebrew_packages;"}
        ]
        
    else:
        # Linux (Debian/Redhat)
        queries = [
            {"type": "deb", "sql": "SELECT name, version, arch as architecture, source, 'deb' as manager FROM deb_packages;"},
            {"type": "rpm", "sql": "SELECT name, version, arch as architecture, name as source, 'rpm' as manager FROM rpm_packages;"},
            {"type": "snap", "sql": "SELECT name, version, 'snap' as manager FROM snap_packages;"}
        ]

    # 2. Add Universal Managers (Pip, NPM, Docker, etc.)
    # These work on ALL OSs if osquery is configured correctly
    queries.append({"type": "pip", "sql": "SELECT name, version, 'pip' as manager FROM python_packages;"})
    queries.append({"type": "chrome_ext", "sql": "SELECT name, version, 'chrome_extension' as manager FROM chrome_extensions;"})

    # 3. Execute Loop
    for q in queries:
        try:
            res = subprocess.run([OSQUERY, "--json", q['sql']], capture_output=True)
            if res.returncode == 0:
                items = json.loads(res.stdout)
                # Normalize data (ensure 'source' exists)
                for i in items:
                    if not i.get('source'): i['source'] = i['name']
                inventory.extend(items)
        except: pass

    return inventory