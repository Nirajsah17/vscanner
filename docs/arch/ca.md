## Create CA private key
openssl genrsa -out ca.key 4096

# Create CA certificate
openssl req -x509 -new -nodes \
  -key ca.key \
  -sha256 \
  -days 3650 \
  -subj "/CN=MyInternalCA" \
  -out ca.crt

* Store ca.key securely (vault/HSM)
* ca.crt will be copied to agent + server


# Server private key
openssl genrsa -out server.key 2048

# Server CSR
openssl req -new \
  -key server.key \
  -subj "/CN=localhost" \
  -out server.csr

# Sign server cert with CA
openssl x509 -req \
  -in server.csr \
  -CA ca.crt \
  -CAkey ca.key \
  -CAcreateserial \
  -out server.crt \
  -days 365



