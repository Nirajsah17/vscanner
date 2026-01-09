import json
import subprocess
from config import conf

OSQUERY = conf.get("osquery_bin")

def get_network_data():
    data = {
        "interfaces": [],
        "dns": [],
        "gateway": "unknown",
        "open_ports": []
    }

    # 1. Interfaces & MAC
    try:
        cmd = "SELECT interface, address, mac FROM interface_details WHERE address NOT LIKE '127.%' AND address NOT LIKE '::1';"
        res = subprocess.run([OSQUERY, "--json", cmd], capture_output=True)
        data['interfaces'] = json.loads(res.stdout)
    except: pass

    # 2. Default Gateway
    try:
        cmd = "SELECT gateway FROM routes WHERE destination = '0.0.0.0' LIMIT 1;"
        res = subprocess.run([OSQUERY, "--json", cmd], capture_output=True)
        routes = json.loads(res.stdout)
        if routes:
            data['gateway'] = routes[0]['gateway']
    except: pass

    # 3. DNS Servers
    try:
        cmd = "SELECT DISTINCT address FROM dns_resolvers;"
        res = subprocess.run([OSQUERY, "--json", cmd], capture_output=True)
        data['dns'] = [x['address'] for x in json.loads(res.stdout)]
    except: pass

    # 4. Open Ports (Crucial for Security)
    # Joins listening_ports with processes to show WHAT is listening
    try:
        cmd = """
        SELECT lp.port, lp.protocol, lp.address, p.name as service_name
        FROM listening_ports lp
        LEFT JOIN processes p ON lp.pid = p.pid
        WHERE lp.address NOT LIKE '127.%' AND lp.address NOT LIKE '::1';
        """
        res = subprocess.run([OSQUERY, "--json", cmd], capture_output=True)
        data['open_ports'] = json.loads(res.stdout)
    except: pass

    return data