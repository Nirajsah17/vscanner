from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

UPLOAD_FOLDER = 'cloud_data'
app = Flask(__name__)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/api/upload_scan', methods=['POST'])
def receive_scan():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error"}), 400

        # --- NEW: PARSE DEVICE INFO ---
        # Check if this is the new "v2" format with device info
        if "device" in data and "inventory" in data:
            hostname = data['device'].get('hostname', 'Unknown')
            ip = data['device'].get('ip', 'Unknown')
            os_name = data['device'].get('os', 'Unknown')
            
            print(f"📝 REGISTERING DEVICE: {hostname} [{ip}]")
            print(f"   OS: {os_name}")
            
            # Use Hostname in filename now!
            filename = f"{hostname}_{ip}.json"
        else:
            # Fallback for old agents
            client_ip = request.remote_addr
            filename = f"scan_{client_ip}.json"

        # Save to disk
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        return jsonify({"status": "success", "message": "Device Registered"}), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error"}), 500
@app.route('/ping', methods=['GET'])
def ping():
    return "PONG", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)