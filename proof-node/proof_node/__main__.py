import logging
from flask import Flask, request, jsonify
import docker
import tempfile
import os
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
docker_client = docker.from_env()


@app.route('/spunup', methods=['POST'])
def spunup():
    data = request.json
    if not data or 'image_url' not in data or 'env_vars' not in data:
        return jsonify({"error": "Missing image_url or env_vars"}), 400

    image_url = data['image_url']
    env_vars = data['env_vars']

    try:
        # Pull the image
        docker_client.images.pull(image_url)

        # Create a temporary directory for Gramine files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a Dockerfile to set up the Gramine environment
            dockerfile_content = f"""
            FROM {image_url}
            RUN apt-get update && apt-get install -y gramine
            COPY python.manifest.template /app/python.manifest.template
            WORKDIR /app
            """
            with open(os.path.join(tmpdir, 'Dockerfile'), 'w') as f:
                f.write(dockerfile_content)

            # Copy the Gramine manifest template
            with open(os.path.join(tmpdir, 'python.manifest.template'), 'w') as f:
                f.write(GRAMINE_MANIFEST_TEMPLATE)

            # Build the Gramine-enabled image
            gramine_image, _ = docker_client.images.build(path=tmpdir, tag='gramine-enabled-image:latest')

            # Run the container with Gramine
            container = docker_client.containers.run(
                'gramine-enabled-image:latest',
                command=['gramine-sgx', 'python3', '-c', 'import os; print("\\n".join([f"{k}={v}" for k, v in os.environ.items()]))'],
                environment=env_vars,
                volumes={'/var/run/aesmd': {'bind': '/var/run/aesmd', 'mode': 'ro'}},
                devices=['/dev/sgx_enclave:/dev/sgx_enclave'],
                detach=True,
                remove=True
            )

            # Wait for the container to finish and get logs
            result = container.wait()
            logs = container.logs().decode('utf-8')

        return jsonify({"result": logs, "exit_code": result['StatusCode']})
    except docker.errors.DockerException as e:
        logger.error(f"Docker error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500


# Gramine manifest template
GRAMINE_MANIFEST_TEMPLATE = """
libos.entrypoint = "python3"

loader.entrypoint = "file:{{ gramine.libos }}"
loader.log_level = "{{ log_level }}"

loader.env.LD_LIBRARY_PATH = "/lib:/usr/lib:/usr/lib/x86_64-linux-gnu"

fs.mounts = [
  { path = "/lib", uri = "file:{{ gramine.runtimedir() }}" },
  { path = "/usr", uri = "file:/usr" },
  { path = "/etc", uri = "file:/etc" },
  { path = "/app", uri = "file:/app" },
]

sgx.debug = true
sgx.nonpie_binary = true
sgx.enclave_size = "2G"
sgx.thread_num = 32

sgx.trusted_files = [
  "file:{{ gramine.libos }}",
  "file:{{ python.stdlib }}/",
  "file:{{ python.distlib }}/",
  "file:{{ gramine.runtimedir() }}/",
  "file:/usr/lib/x86_64-linux-gnu/",
  "file:/app/",
]

sgx.allowed_files = [
  "file:/etc/hosts",
  "file:/etc/resolv.conf",
]
"""

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)