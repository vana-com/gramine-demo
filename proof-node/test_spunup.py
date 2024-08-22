# poetry run python test_spunup.py
import requests
import json

url = "http://127.0.0.1:5000/spunup"
payload = {
    "image_url": "volodvana/test-env-echo:latest",
    "env_vars": {
        "TEST_VAR1": "Hello",
        "TEST_VAR2": "World",
        "CUSTOM_ENV": "This is a custom environment variable"
    }
}
headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, data=json.dumps(payload), headers=headers)

print(f"Status Code: {response.status_code}")
print("Response:")
print(json.dumps(response.json(), indent=2))