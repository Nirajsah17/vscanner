import json
import subprocess
import platform
from config import conf

OSQUERY = conf.get("osquery_bin")
OS_TYPE = platform.system()

def get_services():
    services = []
    query = ""

    # 1. Select Query based on OS
    if OS_TYPE == "Windows":
        # Windows Service Table
        query = "SELECT name, display_name as description, status as active_state FROM services WHERE status = 'RUNNING';"
    elif OS_TYPE == "Darwin":
        # macOS Launchd
        query = "SELECT label as name, name as description, 'active' as active_state FROM launchd WHERE run_at_load = 1;"
    else:
        # Linux Systemd (Default)
        query = "SELECT name, description, active_state FROM systemd_units WHERE id LIKE '%.service' AND active_state = 'active';"

    # 2. Execute
    try:
        res = subprocess.run([OSQUERY, "--json", query], capture_output=True)
        services = json.loads(res.stdout)
    except: 
        pass
        
    return services