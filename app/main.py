import time
import sys
import logging
import os

from config import conf
from logger import setup_logging
import agent_id
import api

from security import enrollment

from collectors import os_info, hardware, network, services, software


def check_root():
    if os.geteuid() != 0:
        print("❌ CRITICAL: Agent must run as root.")
        sys.exit(1)


def run_agent_cycle():
    logging.info("--- Starting Collection Cycle ---")
    start_time = time.time()

    aid = agent_id.get_agent_id()

    payload = {
        "agent_id": aid,
        "timestamp": start_time,
        "asset_summary": os_info.get_os_data(),
        "hardware": hardware.get_hardware_data(),
        "network": network.get_network_data(),
        "services": services.get_services(),
        "inventory": software.get_software_inventory()
    }

    logging.info(f"Collected {len(payload['inventory'])} software items")

    api.upload_payload(payload)
    return start_time


def main():
    check_root()
    setup_logging()

    logging.info("🚀 VScanner Agent starting")

    # 🔐 ENROLLMENT PHASE
    if not enrollment.is_enrolled():
        enrollment.enroll()

    logging.info(f"Agent ID: {agent_id.get_agent_id()}")
    logging.info(f"Server: {conf.get('server_url')}")

    while True:
        try:
            cycle_start = run_agent_cycle()

            interval = conf.get("scan_interval")
            elapsed = time.time() - cycle_start
            sleep_time = max(0, interval - elapsed)

            logging.info(f"Sleeping {int(sleep_time)} seconds")
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            logging.info("Stopping Agent")
            sys.exit(0)

        except Exception as e:
            logging.critical("Unhandled exception", exc_info=True)
            time.sleep(60)


if __name__ == "__main__":
    main()
