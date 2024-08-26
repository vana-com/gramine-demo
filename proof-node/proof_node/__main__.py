import logging
from flask import Flask, request, jsonify
import docker

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

        # Run the container
        container = docker_client.containers.run(
            image_url,
            environment=env_vars,
            command=["python", "-c", env_vars.get('PYTHON_SCRIPT', 'print("No script provided")')],
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