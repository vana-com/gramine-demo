import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_browsing_session(session):
    MIN_DURATION = 60  # 1 minute in seconds
    MIN_PAGES = 3
    VALUABLE_KEYWORDS = {'buy', 'cart', 'checkout'}

    duration = session.get('duration', 0)
    pages = session.get('pages', [])
    
    return (
        duration >= MIN_DURATION and
        len(pages) >= MIN_PAGES and
        any(kw in ' '.join(pages).lower() for kw in VALUABLE_KEYWORDS)
    )

class ValidatorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        logger.info(f"Received POST request from {self.client_address}")
        content_length = int(self.headers['Content-Length'])
        session_data = json.loads(self.rfile.read(content_length))

        is_valid = validate_browsing_session(session_data)
        result = {"is_valid": is_valid}

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
    try:
        run_server()
    except Exception as e:
        logger.error(f"Error starting server: {e}")