import requests
import logging
from config import conf

def upload_payload(payload):
    url = conf.get("server_url")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {conf.get('api_key')}"
    }
    
    try:
        logging.info(f"Uploading scan data ({len(str(payload))} bytes) to {url}...")
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            logging.info("✅ Upload Success")
            return True
        elif resp.status_code == 401:
            logging.critical("❌ Auth Failed: Check API Key")
        else:
            logging.warning(f"⚠️ Upload Failed: Server returned {resp.status_code}")
            
    except Exception as e:
        logging.error(f"❌ Connection Error: {e}")
        
    return False