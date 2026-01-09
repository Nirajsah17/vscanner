import json
import subprocess
import time
from config import conf

OSQUERY = conf.get("osquery_bin")

def get_os_data():
    data = {
        "hostname": "unknown",
        "os_name": "unknown",
        "os_version": "unknown",
        "uptime_seconds": 0,
        "last_boot": "unknown",
        "last_login": {}
    }

    # 1. Hostname
    try:
        res = subprocess.run([OSQUERY, "--json", "SELECT hostname FROM system_info;"], capture_output=True)
        data['hostname'] = json.loads(res.stdout)[0]['hostname']
    except: pass

    # 2. OS Version
    try:
        res = subprocess.run([OSQUERY, "--json", "SELECT name, version FROM os_version;"], capture_output=True)
        row = json.loads(res.stdout)[0]
        data['os_name'] = row['name']
        data['os_version'] = row['version']
    except: pass

    # 3. Uptime & Last Boot
    try:
        res = subprocess.run([OSQUERY, "--json", "SELECT uptime FROM uptime;"], capture_output=True)
        uptime = int(json.loads(res.stdout)[0]['uptime'])
        data['uptime_seconds'] = uptime
        # Calculate boot time
        boot_ts = time.time() - uptime
        data['last_boot'] = time.ctime(boot_ts)
    except: pass

    # 4. Last User Login
    try:
        # Get the most recent login
        cmd = "SELECT user, time, host FROM last ORDER BY time DESC LIMIT 1;"
        res = subprocess.run([OSQUERY, "--json", cmd], capture_output=True)
        logins = json.loads(res.stdout)
        if logins:
            data['last_login'] = logins[0]
            # Convert Unix timestamp to readable
            if 'time' in data['last_login']:
                data['last_login']['time_str'] = time.ctime(int(data['last_login']['time']))
    except: pass

    return data