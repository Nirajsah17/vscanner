import os
import uuid
import logging
from config import conf

def get_agent_id():
    id_file = conf.get("agent_id_file")
    
    # 1. Read existing ID
    if os.path.exists(id_file):
        with open(id_file, 'r') as f:
            agent_uuid = f.read().strip()
            if agent_uuid:
                return agent_uuid

    # 2. Generate new ID if missing
    new_id = str(uuid.uuid4())
    try:
        os.makedirs(os.path.dirname(id_file), exist_ok=True)
        with open(id_file, 'w') as f:
            f.write(new_id)
        logging.info(f"Generated new Agent ID: {new_id}")
    except Exception as e:
        logging.error(f"Failed to save Agent ID: {e}")
    
    return new_id