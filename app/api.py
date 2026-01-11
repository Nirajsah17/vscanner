import requests
import logging
from config import conf

CERT_DIR = conf.get("cert_dir")

CLIENT_CERT = (
    f"{CERT_DIR}/agent.crt",
    f"{CERT_DIR}/agent.key"
)

CA_CERT = f"{CERT_DIR}/ca.crt"


def upload_payload(payload):
    try:
        r = requests.post(
            f"{conf.get('server_url')}/upload_scan",
            json=payload,
            cert=CLIENT_CERT,
            verify=CA_CERT,
            timeout=15
        )
        r.raise_for_status()
        logging.info("Payload uploaded successfully")

    except Exception as e:
        logging.error(f"Upload failed: {e}")
        raise
