import os
import json
import logging
import docker
import requests
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)
client = docker.from_env()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_image(url):
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as temp_file:
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)

    return temp_file.name


def run_signed_container(image_path, environment):
    container_name = f"dynamic-proof-{os.path.basename(image_path).replace('.tar.gz', '')}"

    # Load the image
    try:
        with open(image_path, 'rb') as image_file:
            image = client.images.load(image_file.read())[0]
        logger.info(f"Loaded image: {image.tags}")
    except Exception as e:
        logger.error(f"Error loading image: {str(e)}")
        raise

    # Prepare SGX-specific configurations
    sgx_enabled = os.environ.get('SGX') == 'true'
    devices = ['/dev/sgx_enclave:/dev/sgx_enclave'] if sgx_enabled else None
    volumes = {
        '/var/run/aesmd': {'bind': '/var/run/aesmd', 'mode': 'rw'},
        f'/mnt/sealed/{container_name}': {'bind': '/sealed', 'mode': 'rw'},
        '/gsc-my-proof/input': {'bind': '/input', 'mode': 'rw'},
        '/gsc-my-proof/output': {'bind': '/output', 'mode': 'rw'}
    } if sgx_enabled else None

    # Include IAS_API_KEY in the environment variables
    ias_api_key = os.environ.get('IAS_API_KEY')
    if ias_api_key:
        environment['IAS_API_KEY'] = ias_api_key

    if sgx_enabled:
        environment['SGX_AESM_ADDR'] = '1'

    # Run the container
    try:
        container = client.containers.run(
            image=image.id,
            detach=True,
            name=container_name,
            devices=devices,
            volumes=volumes,
            environment=environment,
            remove=False  # Changed to False
        )

        # Wait for the container to finish
        result = container.wait()

        # Get the logs
        logs = container.logs().decode('utf-8')

        logger.info(f"Container {container_name} finished with exit code {result['StatusCode']}")
        logger.info(f"Container logs:\n{logs}")

        # Remove the container
        container.remove()

        return result['StatusCode'], logs
    except Exception as e:
        logger.error(f"Error running container: {str(e)}")
        raise


@app.route('/run_proof', methods=['POST'])
def run_proof():
    data = request.json
    image_url = data.get('image_url')
    environment = data.get('environment', {})

    if not image_url:
        return jsonify({'error': 'Missing image_url'}), 400

    try:
        # Download the image
        image_path = download_image(image_url)
        logger.info(f"Downloaded image to: {image_path}")

        # Run the container
        exit_code, logs = run_signed_container(image_path, environment)

        # Clean up the downloaded image
        os.unlink(image_path)

        return jsonify({
            'status': 'success',
            'exit_code': exit_code,
            'logs': logs
        })

    except Exception as e:
        logger.error(f"Error running proof: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)