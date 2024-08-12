import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

class ValidatorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
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

    def do_GET(self):
        if self.path == '/attestation':
            logger.info(f"Received GET request for attestation from {self.client_address}")
            attestation_report = get_attestation_report()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"attestation": attestation_report}).encode('utf-8'))
            logger.info("Sent attestation report")
        else:
            logger.info(f"Received GET request from {self.client_address}")
            sealed_data = unseal_data()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(sealed_data).encode('utf-8'))
            logger.info("Returned sealed data")

def run_server():
    server_address = ('0.0.0.0', 8000)
    httpd = HTTPServer(server_address, ValidatorHandler)
    logger.info('Starting validator server on 0.0.0.0:8000...')
    httpd.serve_forever()

if __name__ == "__main__":
    logger.info("Starting validator server...")
    os.makedirs("/sealed", exist_ok=True)

    try:
        run_server()
    except Exception as e:
        logger.error(f"Error starting server: {e}")