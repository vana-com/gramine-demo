import random
import time
import logging
from flask import Flask, request, jsonify
import docker

from .client import process_task

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
            detach=True,
            remove=False  # Changed to False to prevent automatic container removal to read from logs
        )

        # Wait for the container to finish
        result = container.wait()

        # Get the container logs
        logs = container.logs().decode('utf-8')

        # Remove the container
        container.remove()

        return jsonify({"result": logs, "exit_code": result['StatusCode']})
    except docker.errors.DockerException as e:
        logger.error(f"Docker error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

def main():
    logging.info("Starting client")

    while True:
        task = random.choice([
            {
                "validator_type": "doordash",
                "data": {
                    "id": str(random.randint(1, 1000)),
                    "name": f"User {random.randint(1, 100)}",
                    "email": f"user{random.randint(1, 100)}@example.com",
                    "phone": f"{random.randint(1000000000, 9999999999)}"
                }
            },
            {
                "validator_type": "analytics",
                "data": {
                    "duration": random.randint(30, 300),
                    "pages": [f"page_{random.randint(1, 10)}" for _ in range(random.randint(1, 10))] +
                             random.choice([["cart"], ["checkout"], ["buy"], []])
                }
            }
        ])

        if task["validator_type"] == "doordash" and random.random() < 0.2:
            task["data"].pop("phone", None)

        logging.info(f"Generated task: {task}")
        process_task(task)

        time.sleep(random.uniform(1, 5))


if __name__ == "__main__":
    logging.info("Starting main")
    app.run(host='0.0.0.0', port=5000)