import os
import socket
import requests
from config import conf
import logging

CERT_DIR = conf.get("cert_dir")
CA_CERT = f"{CERT_DIR}/ca.crt"
AGENT_CERT = f"{CERT_DIR}/agent.crt"
AGENT_KEY = f"{CERT_DIR}/agent.key"


def is_alive():
    try:
        r = requests.get(
            f"{conf.get('server_url')}/api/ping",
            verify=CA_CERT,
            timeout=5
        )
        return r.status_code == 200
    except requests.RequestException:
        return False

def is_enrolled():
    return os.path.exists(AGENT_CERT) and os.path.exists(AGENT_KEY)


def enroll():
    logging.info("Agent not enrolled. Starting enrollment.")
    islive = is_alive()
    logging.info("Server is live: %s", islive)

    payload = {
        "host_id": socket.gethostname(),
        "enroll_secret": conf.get("enroll_secret")
    }
    logging.info(f"Sending enrollment request to {conf.get('server_url')}/enroll")
    r = requests.post(
        f"{conf.get('server_url')}/enroll",
        json=payload,
        verify=CA_CERT,
        timeout=10
    )
    
    logging.info(f"Sending enrollment request :{r.raise_for_status()}")

    r.raise_for_status()
    data = r.json()

    with open(AGENT_CERT, "w") as f:
        f.write(data["cert"])
    with open(AGENT_KEY, "w") as f:
        f.write(data["key"])

    os.chmod(AGENT_KEY, 0o600)
    logging.info("Enrollment successful. Certificate installed.")
