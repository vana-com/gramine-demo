import logging
from flask import Flask, request, jsonify
import docker
import os
import tempfile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
docker_client = docker.from_env()

def create_manifest(env_vars):
    manifest_content = """
loader.entrypoint = "file:{{ gramine.libos }}"
libos.entrypoint = "/usr/bin/python3"

loader.log_level = "{{ log_level }}"

loader.env.LD_LIBRARY_PATH = "/lib:/usr/lib:/usr/local/lib:/lib/x86_64-linux-gnu"

fs.mounts = [
  {{ path = "/lib", uri = "file:/lib" }},
  {{ path = "/usr", uri = "file:/usr" }},
  {{ path = "/etc", uri = "file:/etc" }},
  {{ path = "/bin", uri = "file:/bin" }},
]

sgx.debug = true
sgx.nonpie_binary = true
sgx.enclave_size = "256M"
sgx.thread_num = 4

sgx.trusted_files = [
  "file:{{ gramine.libos }}",
  "file:/usr/bin/python3",
  "file:/usr/lib/python3.9/",
  "file:/lib/x86_64-linux-gnu/",
]

loader.env.PYTHON_SCRIPT = "{env_vars.get('PYTHON_SCRIPT', 'print(\"No script provided\")')}"
"""

    for key, value in env_vars.items():
        if key != 'PYTHON_SCRIPT':
            manifest_content += f'loader.env.{key} = "{value}"\n'

    return manifest_content

@app.route('/spunup', methods=['POST'])
def spunup():
    data = request.json
    if not data or 'env_vars' not in data:
        return jsonify({"error": "Missing env_vars"}), 400

    env_vars = data['env_vars']

    try:
        # Create a temporary directory to store the manifest
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Create the manifest file
            manifest_content = create_manifest(env_vars)
            manifest_path = os.path.join(tmpdirname, 'python.manifest')
            with open(manifest_path, 'w') as f:
                f.write(manifest_content)

            # Run the container with Gramine
            container = docker_client.containers.run(
                "proof-node:latest",  # Use our custom image
                command=[
                    "gramine-sgx",
                    "python3",
                    "-c",
                    env_vars.get('PYTHON_SCRIPT', 'print("No script provided")')
                ],
                volumes={
                    manifest_path: {'bind': '/python.manifest', 'mode': 'ro'},
                    '/var/run/aesmd': {'bind': '/var/run/aesmd', 'mode': 'rw'}
                },
                devices=['/dev/sgx_enclave'],
                environment=env_vars,
                detach=True,
                remove=True
            )

            # Wait for the container to finish and get logs
            logs = container.logs(stream=True)
            result = "".join([log.decode() for log in logs])

            return jsonify({"result": result, "exit_code": container.wait()['StatusCode']})
    except docker.errors.DockerException as e:
        logger.error(f"Docker error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == "__main__":
    logging.info("Starting main")
    app.run(host='0.0.0.0', port=5000)