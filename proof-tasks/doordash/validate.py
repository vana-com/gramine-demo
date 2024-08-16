import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import os
import base64

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add this near the top of the file, after the logger setup
IAS_API_KEY = os.environ.get('IAS_API_KEY')
logger.info(f"IAS_API_KEY at startup: {IAS_API_KEY}")

SEALED_FILE_PATH = "/sealed/sealed_data.txt"

def get_random_number():
    return requests.get("https://www.randomnumberapi.com/api/v1.0/random").json()[0]

def validate_doordash_profile(profile):
    required_fields = ['id', 'name', 'email', 'phone']
    return all(field in profile for field in required_fields) and get_random_number() > 50

def seal_data(data):
    with open(SEALED_FILE_PATH, 'w') as f:
        json.dump(data, f)
    logger.info(f"Data sealed to {SEALED_FILE_PATH}")

def unseal_data():
    try:
        with open(SEALED_FILE_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_attestation_report():
    try:
        with open('/dev/attestation/report', 'rb') as f:
            report = f.read()
        logger.info('Fetched attestation report successfully')
        return report.hex()  # Return report in hexadecimal format
    except Exception as e:
        logger.error(f'Failed to fetch attestation report: {e}')
        return None

IAS_URL = "https://api.trustedservices.intel.com/sgx/dev/attestation/v4/report"

def verify_with_ias(quote):
    print(f"IAS_API_KEY at verify_with_ias: {IAS_API_KEY}")
    if not IAS_API_KEY:
        logger.error("IAS_API_KEY environment variable not set")
        return None

    headers = {
        "Ocp-Apim-Subscription-Key": IAS_API_KEY,
        "Content-Type": "application/json",
    }
    data = {"isvEnclaveQuote": base64.b64encode(quote).decode()}

    response = requests.post(IAS_URL, headers=headers, json=data)

    if response.status_code == 200:
        return response
    else:
        logger.error(f"IAS verification failed: {response.text}")
        return None

# The following imports and constants are typically part of the client code
# They are included here for testing purposes
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.backends import default_backend

# This certificate would normally be part of the client's trusted certificates
INTEL_SGX_ROOT_CA_CERT_PEM = """
-----BEGIN CERTIFICATE-----
MIIFSzCCA7OgAwIBAgIJANEHdl0yo7CUMA0GCSqGSIb3DQEBCwUAMH4xCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJDQTEUMBIGA1UEBwwLU2FudGEgQ2xhcmExGjAYBgNV
BAoMEUludGVsIENvcnBvcmF0aW9uMTAwLgYDVQQDDCdJbnRlbCBTR1ggQXR0ZXN0
YXRpb24gUmVwb3J0IFNpZ25pbmcgQ0EwIBcNMTYxMTE0MTUzNzMxWhgPMjA0OTEy
MzEyMzU5NTlaMH4xCzAJBgNVBAYTAlVTMQswCQYDVQQIDAJDQTEUMBIGA1UEBwwL
U2FudGEgQ2xhcmExGjAYBgNVBAoMEUludGVsIENvcnBvcmF0aW9uMTAwLgYDVQQD
DCdJbnRlbCBTR1ggQXR0ZXN0YXRpb24gUmVwb3J0IFNpZ25pbmcgQ0EwggGiMA0G
CSqGSIb3DQEBAQUAA4IBjwAwggGKAoIBgQCfPGR+tXc8u1EtJzLA10Feu1Wg+p7e
LmSRmeaCHbkQ1TF3Nwl3RmpqXkeGzNLd69QUnWovYyVSndEMyYc3sHecGgfinEeh
rgBJSEdsSJ9FpaFdesjsxqzGRa20PYdnnfWcCTvFoulpbFR4VBuXnnVLVzkUvlXT
L/TAnd8nIZk0zZkFJ7P5LtePvykkar7LcSQO85wtcQe0R1Raf/sQ6wYKaKmFgCGe
NpEJUmg4ktal4qgIAxk+QHUxQE42sxViN5mqglB0QJdUot/o9a/V/mMeH8KvOAiQ
byinkNndn+Bgk5sSV5DFgF0DffVqmVMblt5p3jPtImzBIH0QQrXJq39AT8cRwP5H
afuVeLHcDsRp6hol4P+ZFIhu8mmbI1u0hH3W/0C2BuYXB5PC+5izFFh/nP0lc2Lf
6rELO9LZdnOhpL1ExFOq9H/B8tPQ84T3Sgb4nAifDabNt/zu6MmCGo5U8lwEFtGM
RoOaX4AS+909x00lYnmtwsDVWv9vBiJCXRsCAwEAAaOByTCBxjBgBgNVHR8EWTBX
MFWgU6BRhk9odHRwOi8vdHJ1c3RlZHNlcnZpY2VzLmludGVsLmNvbS9jb250ZW50
L0NSTC9TR1gvQXR0ZXN0YXRpb25SZXBvcnRTaWduaW5nQ0EuY3JsMB0GA1UdDgQW
BBR4Q3t2pn680K9+QjfrNXw7hwFRPDAfBgNVHSMEGDAWgBR4Q3t2pn680K9+Qjfr
NXw7hwFRPDAOBgNVHQ8BAf8EBAMCAQYwEgYDVR0TAQH/BAgwBgEB/wIBADANBgkq
hkiG9w0BAQsFAAOCAYEAeF8tYMXICvQqeXYQITkV2oLJsp6J4JAqJabHWxYJHGir
IEqucRiJSSx+HjIJEUVaj8E0QjEud6Y5lNmXlcjqRXaCPOqK0eGRz6hi+ripMtPZ
sFNaBwLQVV905SDjAzDzNIDnrcnXyB4gcDFCvwDFKKgLRjOB/WAqgscDUoGq5ZVi
zLUzTqiQPmULAQaB9c6Oti6snEFJiCQ67JLyW/E83/frzCmO5Ru6WjU4tmsmy8Ra
Ud4APK0wZTGtfPXU7w+IBdG5Ez0kE1qzxGQaL4gINJ1zMyleDnbuS8UicjJijvqA
152Sq049ESDz+1rRGc2NVEqh1KaGXmtXvqxXcTB+Ljy5Bw2ke0v8iGngFBPqCTVB
3op5KBG3RjbF6RRSzwzuWfL7QErNC8WEy5yDVARzTA5+xmBc388v9Dm21HGfcC8O
DD+gT9sSpssq0ascmvH49MOgjt1yoysLtdCtJW/9FZpoOypaHx0R+mJTLwPXVMrv
DaVzWh5aiEx+idkSGMnX
-----END CERTIFICATE-----
"""

# The following functions would typically be part of the client code
# They are included here for testing purposes
def verify_certificate_chain(cert_chain):
    root_cert = x509.load_pem_x509_certificate(INTEL_SGX_ROOT_CA_CERT_PEM.encode(), default_backend())

    for i in range(len(cert_chain) - 1, 0, -1):
        issuer = cert_chain[i-1]
        cert = cert_chain[i]

        try:
            issuer.public_key().verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm
            )
        except:
            return False

    if cert_chain[0].public_bytes(serialization.Encoding.PEM) != root_cert.public_bytes(serialization.Encoding.PEM):
        return False

    return True

def verify_ias_report(ias_report, ias_signature, ias_certs):
    cert_chain = x509.load_pem_x509_certificates(ias_certs.encode(), default_backend())

    if not verify_certificate_chain(cert_chain):
        return False

    leaf_cert = cert_chain[-1]
    public_key = leaf_cert.public_key()

    try:
        public_key.verify(
            base64.b64decode(ias_signature),
            json.dumps(ias_report).encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except:
        return False

class ValidatorHandler(BaseHTTPRequestHandler):
    def get_attestation_data(self):
        quote = get_attestation_report()
        if not quote:
            return None, "Failed to get attestation report"

        ias_response = verify_with_ias(quote)
        if not ias_response:
            return None, "IAS verification failed"

        attestation_data = {
            'ias_report': ias_response.json(),
            'ias_signature': ias_response.headers.get('X-IASReport-Signature'),
            'ias_certs': ias_response.headers.get('X-IASReport-Signing-Certificate')
        }
        return attestation_data, None

    def verify_attestation(self, attestation_data, expected_mrenclave=None):
        if not verify_ias_report(attestation_data['ias_report'], attestation_data['ias_signature'], attestation_data['ias_certs']):
            return "IAS report verification failed"

        quote_status = attestation_data['ias_report']['isvEnclaveQuoteStatus']
        if quote_status.lower() != "ok":
            return f"Quote status is not OK: {quote_status}"

        if expected_mrenclave:
            actual_mrenclave = attestation_data['ias_report']['isvEnclaveQuoteBody']['mrenclave']
            if actual_mrenclave != expected_mrenclave:
                return f"MRENCLAVE mismatch. Expected: {expected_mrenclave}, Actual: {actual_mrenclave}"

        return None

    def do_GET(self):
        if self.path == '/attestation':
            attestation_data, error = self.get_attestation_data()
            if error:
                self.send_error(500, error)
                return

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(attestation_data).encode('utf-8'))
            logger.info("Sent attestation data")
        else:
            logger.info(f"Received GET request from {self.client_address}")
            sealed_data = unseal_data()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(sealed_data).encode('utf-8'))
            logger.info("Returned sealed data")

    def do_POST(self):
        if self.path == '/test_attestation':
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
            expected_mrenclave = post_data.get('expected_mrenclave')

            attestation_data, error = self.get_attestation_data()
            if error:
                self.send_error(500, error)
                return

            error = self.verify_attestation(attestation_data, expected_mrenclave)
            if error:
                self.send_error(400, error)
                return

            # If we've made it this far, attestation is successful
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Attestation verified successfully"}).encode('utf-8'))
            logger.info("Attestation verified successfully")
        else:
            logger.info(f"Received POST request from {self.client_address}")
            content_length = int(self.headers['Content-Length'])
            profile_data = json.loads(self.rfile.read(content_length))

            is_valid = validate_doordash_profile(profile_data)
            result = {"is_valid": is_valid}

            # Seal the data as a side effect
            seal_data(profile_data)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            logger.info(f"Processed validation request. Result: {result}")

def run_server():
    server_address = ('0.0.0.0', 8000)
    httpd = HTTPServer(server_address, ValidatorHandler)
    logger.info('Starting validator server on 0.0.0.0:8000...')
    httpd.serve_forever()

if __name__ == "__main__":
    logger.info("Starting validator server...")
    logger.info(f"IAS_API_KEY before server start: {IAS_API_KEY}")
    os.makedirs("/sealed", exist_ok=True)

    try:
        run_server()
    except Exception as e:
        logger.error(f"Error starting server: {e}")