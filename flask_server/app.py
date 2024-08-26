import os
import docker
from flask import Flask, request, jsonify

app = Flask(__name__)
client = docker.from_env()

@app.route('/run_container', methods=['POST'])
def run_container():
    data = request.json
    image_url = data.get('image_url')
    env_vars = data.get('env_vars', {})

    try:
        # Pull the image if it's not already present
        client.images.pull(image_url)

        # Run the container with Gramine
        container = client.containers.run(
            image_url,
            environment=env_vars,
            detach=True,
            remove=True,
            runtime='rune',
            devices=['/dev/sgx/enclave:/dev/sgx/enclave'],
            volumes={'/var/run/aesmd:/var/run/aesmd': {'bind': '/var/run/aesmd', 'mode': 'ro'}}
        )

        # Wait for the container to finish and get the logs
        result = container.wait()
        logs = container.logs().decode('utf-8')

        return jsonify({
            'status': 'success',
            'exit_code': result['StatusCode'],
            'output': logs
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)