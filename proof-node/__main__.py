import logging
from flask import Flask, request, jsonify
import docker
import tempfile
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
docker_client = docker.from_env()

def create_manifest(image_url, env_vars):
    manifest_content = f"""
loader.entrypoint = "file:{{ gramine.libos }}"
libos.entrypoint = "/usr/local/bin/python"

loader.log_level = "{{ log_level }}"

loader.env.LD_LIBRARY_PATH = "/lib:/usr/lib:/usr/local/lib:/lib/x86_64-linux-gnu"

fs.mounts = [
  {{ path = "/lib", uri = "file:/lib" }},
  {{ path = "/usr", uri = "file:/usr" }},
  {{ path = "/etc", uri = "file:/etc" }},
  {{ path = "/bin", uri = "file:/bin" }},
  {{ path = "/app", uri = "file:/app" }},
]

sgx.debug = true
sgx.nonpie_binary = true
sgx.enclave_size = "256M"
sgx.thread_num = 4

sgx.trusted_files = [
  "file:{{ gramine.libos }}",
  "file:/usr/local/bin/python",
  "file:/usr/lib/python3.9/",
  "file:/usr/local/lib/python3.9/",
  "file:/lib/x86_64-linux-gnu/",
  "file:/app/print_env.py",
]
"""

    for key, value in env_vars.items():
        manifest_content += f'loader.env.{key} = "{value}"
'

    return manifest_content

@app.route('/run', methods=['POST'])
def run_container():
    data = request.json
    if not data or 'image_url' not in data or 'env_vars' not in data:
        return jsonify({"error": "Missing image_url or env_vars"}), 400

    image_url = data['image_url']
    env_vars = data['env_vars']

    try:
        # Pull the image
        docker_client.images.pull(image_url)

        # Create a temporary directory to store the manifest
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Create the manifest file
            manifest_content = create_manifest(image_url, env_vars)
            manifest_path = os.path.join(tmpdirname, 'python.manifest')
            with open(manifest_path, 'w') as f:
                f.write(manifest_content)

            # Run the container with Gramine-SGX
            container = docker_client.containers.run(
                image_url,
                command=[
                    "gramine-sgx",
                    "python",
                    "/app/print_env.py"
                ],
                volumes={
                    manifest_path: {'bind': '/python.manifest', 'mode': 'ro'},
                    '/var/run/aesmd': {'bind': '/var/run/aesmd', 'mode': 'rw'}
                },
                devices=['/dev/sgx_enclave'],
                environment=env_vars,
                remove=True
            )

            # Get logs
            logs = container.logs().decode()
            logger.info(f"Container logs: {logs}")

            return jsonify({"result": logs})
    except docker.errors.DockerException as e:
        logger.error(f"Docker error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)