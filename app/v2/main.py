import time
import sys
import logging
import os

# Import Modules
from config import conf
from logger import setup_logging
import agent_id
import api

# Import Collectors
from collectors import os_info, hardware, network, services, software

def check_root():
    if os.geteuid() != 0:
        print("❌ CRITICAL: Agent must run as root.")
        sys.exit(1)

def run_agent_cycle():
    logging.info("--- Starting Collection Cycle ---")
    start_time = time.time()

    # 1. Identify Agent
    aid = agent_id.get_agent_id()

    # 2. Run Collectors
    payload = {
        "agent_id": aid,
        "timestamp": start_time,
        "asset_summary": os_info.get_os_data(),
        "hardware": hardware.get_hardware_data(),
        "network": network.get_network_data(),
        "services": services.get_services(),
        "inventory": software.get_software_inventory()
    }

    logging.info(f"Collection complete. Found {len(payload['inventory'])} software items.")

    # 3. Upload
    api.upload_payload(payload)

    return start_time

def main():
    # Boot Sequence
    check_root()
    setup_logging()
    
    logging.info(f"🚀 VScanner Agent v2.0 Started. ID: {agent_id.get_agent_id()}")
    logging.info(f"Server: {conf.get('server_url')}")

    while True:
        try:
            cycle_start = run_agent_cycle()
            
            # Calculate Sleep
            interval = conf.get("scan_interval")
            elapsed = time.time() - cycle_start
            sleep_time = max(0, interval - elapsed)
            
            logging.info(f"Sleeping for {int(sleep_time)} seconds...")
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            logging.info("Stopping Agent...")
            sys.exit(0)
        except Exception as e:
            logging.critical(f"Unhandled Exception in Main Loop: {e}", exc_info=True)
            time.sleep(60) # Safety backoff

if __name__ == "__main__":
    main()