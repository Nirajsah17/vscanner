import ssl
import json
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8443
ENROLL_SECRET = "super-secret"

BASE = os.path.dirname(__file__)
CA_CERT = "../certs/ca/ca.crt"
CA_KEY = "../certs/ca/ca.key"
SERVER_CERT = "../certs/server/server.crt"
SERVER_KEY = "../certs/server/server.key"
ISSUED = "./issued"

os.makedirs(ISSUED, exist_ok=True)


def issue_client_cert(host_id):
    key = f"{ISSUED}/{host_id}.key"
    csr = f"{ISSUED}/{host_id}.csr"
    crt = f"{ISSUED}/{host_id}.crt"

    subprocess.run(["openssl", "genrsa", "-out", key, "2048"], check=True)

    subprocess.run([
        "openssl", "req", "-new",
        "-key", key,
        "-subj", f"/CN={host_id}",
        "-out", csr
    ], check=True)

    subprocess.run([
        "openssl", "x509", "-req",
        "-in", csr,
        "-CA", CA_CERT,
        "-CAkey", CA_KEY,
        "-CAcreateserial",
        "-out", crt,
        "-days", "7"
    ], check=True)

    return open(crt).read(), open(key).read()


class Handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == "/api/ping":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = {"status": "ok"}
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        # Default: Not Found
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        self.wfile.write(
            json.dumps({"error": "Not Found"}).encode("utf-8")
        )
        
    def do_POST(self):
        print("Received POST to", self.path)
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        
        if self.path == "/api/enroll":
            if body.get("enroll_secret") != ENROLL_SECRET:
                self.send_response(403)
                self.end_headers()
                return

            cert, key = issue_client_cert(body["host_id"])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                "cert": cert,
                "key": key
            }).encode())

        elif self.path == "/api/upload_scan":
            peer = self.connection.getpeercert()
            print("Facts from:", peer["subject"])
            print(body)

            self.send_response(200)
            self.end_headers()

    def log_message(self, *_):
        pass


httpd = HTTPServer(("0.0.0.0", PORT), Handler)

ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ctx.load_cert_chain(SERVER_CERT, SERVER_KEY)
ctx.load_verify_locations(CA_CERT)
ctx.verify_mode = ssl.CERT_OPTIONAL

httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

print("Server running on https://localhost:8443")
httpd.serve_forever()
