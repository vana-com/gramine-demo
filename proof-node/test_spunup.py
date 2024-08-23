import requests
import json

url = "http://localhost:5000/spunup"
payload = {
    "image_url": "python:3.9-slim",  # Using a standard Python image for testing
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

if response.status_code == 200:
    print("\nEnvironment Variables:")
    for line in response.json()['result'].split('\n'):
        print(line)
    print(f"\nExit Code: {response.json()['exit_code']}")