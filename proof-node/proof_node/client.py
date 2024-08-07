import docker
import time
import json
import os
import atexit
import signal
import sys
import logging
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_VALIDATORS = int(os.environ.get('MAX_VALIDATORS', 3))
try:
    client = docker.from_env(version='auto')
    client.ping()  # Test the connection
    logger.info("Connected to Docker")
except docker.errors.DockerException as e:
    logger.error(f"Error connecting to Docker: {e}")
    sys.exit(1)

active_validators = {}

def get_or_create_validator(validator_type):
    container_name = f'{validator_type}-proof'
    
    # Check if a container with the given name already exists
    existing_containers = client.containers.list(all=True, filters={'name': container_name})
    
    if existing_containers:
        container = existing_containers[0]
        if container.status != 'running':
            container.start()
        logger.info(f"Reusing existing validator: {container_name}")
        return container
    
    if len(active_validators) >= MAX_VALIDATORS:
        oldest_type = min(active_validators, key=lambda k: active_validators[k].attrs['Created'])
        oldest_validator = active_validators.pop(oldest_type)
        oldest_validator.stop()
        oldest_validator.remove()
        logger.info(f"Removed oldest validator: {oldest_type}")

    validator = client.containers.run(
        f'{validator_type}-proof',
        detach=True,
        name=container_name,
        stdin_open=True,
        tty=True
    )
    
    active_validators[validator_type] = validator
    logger.info(f"Created new validator: {validator_type}")
    return validator

def process_task(task):
    validator_type = task['validator_type']
    data = task['data']
    
    validator = get_or_create_validator(validator_type)
    
    task_data = json.dumps(data)
    
    exec_result = validator.exec_run(
        cmd=["sh", "-c", f"echo '{task_data}' | python /app/validate.py"],
        stdout=True,
        stderr=True
    )
    
    output = exec_result.output.decode().strip()
    exit_code = exec_result.exit_code
    
    if exit_code != 0:
        logger.error(f"Error processing task: {output}")
        return False
    
    try:
        result = json.loads(output)
        logger.info(f"Processing task for {validator_type}: {data}")
        logger.info(f"Validation result: {result}")
        return result['is_valid']
    except json.JSONDecodeError:
        logger.error(f"Error decoding validator output: {output}")
        return False

def cleanup(signum=None, frame=None):
    logger.info("Starting cleanup process")
    for validator_type in list(active_validators.keys()):
        container_name = f'{validator_type}-proof'
        try:
            container = client.containers.get(container_name)
            logger.info(f"Stopping validator {container.name}")
            container.stop()
            logger.info(f"Removing validator {container.name}")
            container.remove()
            logger.info(f"Successfully removed validator {container.name}")
            del active_validators[validator_type]
        except docker.errors.NotFound:
            logger.info(f"Container {container_name} not found, skipping")
        except docker.errors.APIError as e:
            logger.error(f"Error cleaning up validator {container_name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error cleaning up validator {container_name}: {e}")
    logger.info("Cleanup process completed")
    sys.exit(0)

# atexit.register(cleanup)
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)