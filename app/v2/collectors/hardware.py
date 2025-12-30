import json
import subprocess
from config import conf

OSQUERY = conf.get("osquery_bin")

def get_hardware_data():
    data = {
        "cpu": {},
        "ram_gb": 0,
        "volumes": []
    }

    # 1. CPU & RAM
    try:
        cmd = "SELECT cpu_brand, cpu_physical_cores, physical_memory FROM system_info;"
        res = subprocess.run([OSQUERY, "--json", cmd], capture_output=True)
        row = json.loads(res.stdout)[0]
        data['cpu'] = {
            "model": row.get('cpu_brand'),
            "cores": row.get('cpu_physical_cores')
        }
        # Convert bytes to GB
        mem_bytes = int(row.get('physical_memory', 0))
        data['ram_gb'] = round(mem_bytes / (1024**3), 2)
    except: pass

    # 2. Volumes (Disk Space)
    # We filter for physical disks (ext4, xfs, ntfs) to avoid /proc noise
    try:
        cmd = "SELECT device, path, type, total_space, free_space FROM mounts WHERE type IN ('ext4', 'xfs', 'ntfs', 'vfat', 'apfs');"
        res = subprocess.run([OSQUERY, "--json", cmd], capture_output=True)
        mounts = json.loads(res.stdout)
        for m in mounts:
            # Convert bytes to GB
            total = int(m.get('total_space', 0))
            free = int(m.get('free_space', 0))
            m['total_gb'] = round(total / (1024**3), 2)
            m['free_gb'] = round(free / (1024**3), 2)
            data['volumes'].append(m)
    except: pass

    return data