import json
import os
import platform
import sys

# Detect OS
OS_TYPE = platform.system() # 'Linux', 'Windows', or 'Darwin' (macOS)

# 1. Define OS-Specific Paths
if OS_TYPE == "Windows":
    BASE_DIR = r"C:\ProgramData\VScanner"
    CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
    LOG_FILE = os.path.join(BASE_DIR, "logs", "agent.log")
    AGENT_ID_FILE = os.path.join(BASE_DIR, "agent_id")
    DEFAULT_BIN = r"C:\Program Files\osquery\osqueryi.exe"
else:
    # Linux & macOS
    BASE_DIR = "/etc/vscanner"
    CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
    LOG_FILE = "/var/log/vscanner/agent.log"
    AGENT_ID_FILE = os.path.join(BASE_DIR, "agent_id")
    DEFAULT_BIN = "/usr/bin/osqueryi"

# Ensure directories exist
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(BASE_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "server_url": "http://localhost:5000/api/upload_scan",
    "api_key": "CHANGE_ME",
    "scan_interval": 14400,
    "osquery_bin": DEFAULT_BIN,
    "agent_id_file": AGENT_ID_FILE
}

class Config:
    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.data.update(json.load(f))
            except: pass

    def get(self, key):
        return self.data.get(key)

conf = Config()