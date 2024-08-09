import json
import sys
import requests
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import os

global_modifier = 0

def get_random_number():
    response = requests.get("https://www.randomnumberapi.com/api/v1.0/random")
    return response.json()[0]

def validate_doordash_profile(profile):
    required_fields = ['id', 'name', 'email', 'phone']
    random_number = get_random_number()
    return all(field in profile for field in required_fields) and random_number + global_modifier > 50

class SimpleServer(SimpleHTTPRequestHandler):
    def do_GET(self):
        global global_modifier
        global_modifier += 10
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Modifier increased")

def run_server():
    server = HTTPServer(('localhost', 8000), SimpleServer)
    server.serve_forever()

def seal_data(file_path, data):
    with open(file_path, 'w') as f:
        f.write(data)

def unseal_data(file_path):
    with open(file_path, 'r') as f:
        return f.read()

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()

    # Seal data demo
    sealed_file_path = "/sealed/sealed_data.txt"
    data_to_seal = "This is some sensitive data."
    seal_data(sealed_file_path, data_to_seal)

    # Unseal data demo
    unsealed_data = unseal_data(sealed_file_path)
    print(f"Unsealed data: {unsealed_data}")

    profile_data = json.load(sys.stdin)
    is_valid = validate_doordash_profile(profile_data)
    print(json.dumps({"is_valid": is_valid}))