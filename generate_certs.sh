#!/usr/bin/env bash

# Exit immediately if a command fails, treat unset vars as error, fail pipelines early
set -euo pipefail

# -------------------------------
# Configuration
# -------------------------------
BASE_DIR="$(pwd)/certs"
CA_DIR="$BASE_DIR/ca"
SERVER_DIR="$BASE_DIR/server"

CA_KEY="$CA_DIR/ca.key"
CA_CERT="$CA_DIR/ca.crt"

SERVER_KEY="$SERVER_DIR/server.key"
SERVER_CSR="$SERVER_DIR/server.csr"
SERVER_CERT="$SERVER_DIR/server.crt"

CA_CN="MyInternalCA"
SERVER_CN="localhost"

CA_VALID_DAYS=3650
SERVER_VALID_DAYS=365

# -------------------------------
# Helper function
# -------------------------------
log() {
  echo "[INFO] $1"
}

# -------------------------------
# Create directories
# -------------------------------
log "Creating directory structure..."
mkdir -p "$CA_DIR" "$SERVER_DIR"

# -------------------------------
# Generate CA private key
# -------------------------------
if [[ ! -f "$CA_KEY" ]]; then
  log "Generating CA private key..."
  openssl genrsa -out "$CA_KEY" 4096
  chmod 600 "$CA_KEY"
else
  log "CA private key already exists. Skipping."
fi

# -------------------------------
# Generate CA certificate
# -------------------------------
if [[ ! -f "$CA_CERT" ]]; then
  log "Generating CA certificate..."
  openssl req -x509 -new -nodes \
    -key "$CA_KEY" \
    -sha256 \
    -days "$CA_VALID_DAYS" \
    -subj "/CN=${CA_CN}" \
    -out "$CA_CERT"
else
  log "CA certificate already exists. Skipping."
fi

# -------------------------------
# Generate Server private key
# -------------------------------
if [[ ! -f "$SERVER_KEY" ]]; then
  log "Generating Server private key..."
  openssl genrsa -out "$SERVER_KEY" 2048
  chmod 600 "$SERVER_KEY"
else
  log "Server private key already exists. Skipping."
fi

# -------------------------------
# Generate Server CSR
# -------------------------------
if [[ ! -f "$SERVER_CSR" ]]; then
  log "Generating Server CSR..."
  openssl req -new \
    -key "$SERVER_KEY" \
    -subj "/CN=${SERVER_CN}" \
    -out "$SERVER_CSR"
else
  log "Server CSR already exists. Skipping."
fi

# -------------------------------
# Sign Server certificate with CA
# -------------------------------
if [[ ! -f "$SERVER_CERT" ]]; then
  log "Signing Server certificate with CA..."
  openssl x509 -req \
    -in "$SERVER_CSR" \
    -CA "$CA_CERT" \
    -CAkey "$CA_KEY" \
    -CAcreateserial \
    -out "$SERVER_CERT" \
    -days "$SERVER_VALID_DAYS" \
    -sha256
else
  log "Server certificate already exists. Skipping."
fi

# -------------------------------
# Summary
# -------------------------------
log "Certificate generation completed successfully."

echo
echo "Generated files:"
echo "CA Key        : $CA_KEY"
echo "CA Cert       : $CA_CERT"
echo "Server Key    : $SERVER_KEY"
echo "Server CSR    : $SERVER_CSR"
echo "Server Cert   : $SERVER_CERT"
