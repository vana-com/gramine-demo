import logging
from flask import Flask, request, jsonify
import docker
import os
import tempfile
import json
import subprocess
import shutil

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
docker_client = docker.from_env()

def build_gsc_image(image_url):
    try:
        # Pull the original image
        logger.info(f"Pulling image: {image_url}")
        docker_client.images.pull(image_url)

        # Build the GSC image
        logger.info(f"Building GSC image for: {image_url}")
        result = subprocess.run(["gsc", "build", image_url, "/app/generic.manifest", "-c", "/app/config.yaml"],
                                capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"GSC build failed with return code {result.returncode}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)

        logger.debug(f"GSC build output: {result.stdout}")

        # The GSC image name is prefixed with 'gsc-'
        gsc_image_name = f"gsc-{image_url}"

        # Sign the GSC image
        logger.info(f"Signing GSC image: {gsc_image_name}")
        result = subprocess.run(["gsc", "sign-image", gsc_image_name, "-c", "/app/config.yaml"],
                                capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"GSC sign failed with return code {result.returncode}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)

        logger.debug(f"GSC sign output: {result.stdout}")

        return gsc_image_name
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in GSC command: {e}")
        logger.error(f"Command: {e.cmd}")
        logger.error(f"Return Code: {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in build_gsc_image: {str(e)}")
        raise

@app.route('/run', methods=['POST'])
def run_container():
    data = request.json
    if not data or 'image_url' not in data or 'env_vars' not in data:
        return jsonify({"error": "Missing image_url or env_vars"}), 400

    image_url = data['image_url']
    env_vars = data['env_vars']

    try:
        # Build and sign the GSC image
        gsc_image_name = build_gsc_image(image_url)

        # Prepare SGX-specific configurations
        devices = ['/dev/sgx_enclave:/dev/sgx_enclave']
        volumes = {'/var/run/aesmd': {'bind': '/var/run/aesmd', 'mode': 'rw'}}
        environment = {'SGX_AESM_ADDR': '1'}
        environment.update(env_vars)  # Add user-provided environment variables

        # Run the GSC container
        logger.info(f"Running GSC container: {gsc_image_name}")
        container = docker_client.containers.run(
            gsc_image_name,
            command="env",  # Just print environment variables for this example
            devices=devices,
            volumes=volumes,
            environment=environment,
            remove=True
        )

        # Get logs
        logs = container.decode('utf-8')
        logger.info(f"Container logs: {logs}")

        return jsonify({"result": logs})
    except docker.errors.DockerException as e:
        logger.error(f"Docker error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except subprocess.CalledProcessError as e:
        logger.error(f"GSC error: {e}")
        logger.error(f"Command output: {e.output}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)