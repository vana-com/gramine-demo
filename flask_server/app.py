import os
import docker
from docker import APIClient
from flask import Flask, request, jsonify

app = Flask(__name__)

print("Docker environment variables:")
for key, value in os.environ.items():
    if 'DOCKER' in key:
        print(f"{key}: {value}")

print("Attempting to connect to Docker daemon...")
try:
    client = APIClient(base_url='unix://var/run/docker.sock')
    print("Docker client created successfully")
    print(f"Docker version: {client.version()}")
except Exception as e:
    print(f"Error creating Docker client: {str(e)}")
    raise

@app.route('/run_container', methods=['POST'])
def run_container():
    data = request.json
    image_url = data.get('image_url')
    env_vars = data.get('env_vars', {})

    try:
        # Pull the image if it's not already present
        client.pull(image_url)

        # Run the container with Gramine
        container = client.create_container(
            image=image_url,
            environment=env_vars,
            runtime='rune',
            devices=['/dev/sgx/enclave:/dev/sgx/enclave'],
            volumes=['/var/run/aesmd'],
            host_config=client.create_host_config(
                runtime='rune',
                devices=['/dev/sgx/enclave:/dev/sgx/enclave'],
                binds={'/var/run/aesmd': {'bind': '/var/run/aesmd', 'mode': 'ro'}}
            )
        )
        container_id = container['Id']
        client.start(container_id)

        # Wait for the container to finish and get the logs
        exit_code = client.wait(container_id)
        logs = client.logs(container_id).decode('utf-8')

        # Remove the container
        client.remove_container(container_id)

        return jsonify({
            'status': 'success',
            'exit_code': exit_code,
            'output': logs
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)