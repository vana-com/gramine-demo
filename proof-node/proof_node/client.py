import docker
# import json
import os
import signal
import sys
import logging
import time
import requests
import subprocess
import socket

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    client = docker.from_env(version='auto')
    client.ping()  # Test the connection
    logger.info("Connected to Docker")
except docker.errors.DockerException as e:
    logger.error(f"Error connecting to Docker: {e}")
    sys.exit(1)
MAX_VALIDATORS = int(os.environ.get('MAX_VALIDATORS', 3))
BASE_PORT = 8000  # Starting port for validators

active_validators = {}

def get_or_create_validator(validator_type):
    sgx_enabled = os.environ.get('SGX') == 'true'
    container_name = f'gsc-{validator_type}-proof' if sgx_enabled else f'{validator_type}-proof'
    
    # Check if a container with the given name already exists
    existing_containers = client.containers.list(all=True, filters={'name': container_name})
    
    if existing_containers:
        container = existing_containers[0]
        if container.status != 'running':
            container.start()
        logger.info(f"Reusing existing validator: {container_name}")
        active_validators[validator_type] = container
        return container
    
    if len(active_validators) >= MAX_VALIDATORS:
        oldest_type = min(active_validators, key=lambda k: active_validators[k].attrs['Created'])
        oldest_validator = active_validators.pop(oldest_type)
        oldest_validator.stop()
        oldest_validator.remove()
        logger.info(f"Removed oldest validator: {oldest_type}")

    # Determine the host port for this validator
    host_port = BASE_PORT + len(active_validators)

    # Prepare SGX-specific configurations
    devices = ['/dev/sgx_enclave:/dev/sgx_enclave'] if sgx_enabled else None
    volumes = {'/var/run/aesmd': {'bind': '/var/run/aesmd', 'mode': 'rw'}, f'/mnt/sealed/{container_name}': {'bind': '/sealed', 'mode': 'rw'}} if sgx_enabled else None
    environment = {'SGX_AESM_ADDR': '1'} if sgx_enabled else None

    # Remove None values to avoid empty specs
    run_kwargs = {
        'image': f'gsc-{validator_type}-proof' if sgx_enabled else f'{validator_type}-proof',
        'detach': True,
        'name': container_name,
        'ports': {'8000/tcp': host_port},  # Map container port 8000 to a specific host port
        'command': ["python", "/validate.py"],
    }
    if devices:
        run_kwargs['devices'] = devices
    if volumes:
        run_kwargs['volumes'] = volumes
    if environment:
        run_kwargs['environment'] = environment

    validator = client.containers.run(**run_kwargs)
    
    # Check if the container is running
    validator.reload()
    logger.info(f"Created new validator: {validator_type} on host port {host_port}. Status: {validator.status}")

    # Wait for the container to be ready
    max_retries = 5
    for i in range(max_retries):
        validator.reload()
        if validator.status == 'running':
            # Check if the server is actually running
            container_ip = validator.attrs['NetworkSettings']['IPAddress']
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex((container_ip, 8000))
            s.close()
            if result == 0:
                logger.info(f"Validator {validator_type} is ready")
                break
        logger.info(f"Waiting for validator {validator_type} to start... (Attempt {i+1}/{max_retries})")
        time.sleep(2)

    if validator.status != 'running':
        logger.error(f"Validator {validator_type} failed to start. Status: {validator.status}")
        return None

    active_validators[validator_type] = validator
    return validator

def process_task(task):
    validator_type = task['validator_type']
    data = task['data']
    
    validator = get_or_create_validator(validator_type)
    if not validator:
        logger.error(f"Failed to get or create validator for {validator_type}")
        return False
    
    logger.info(f"Starting task for {validator_type}: {data}")

    try:
        # Get the container's IP address
        container_info = client.api.inspect_container(validator.id)
        container_ip = container_info['NetworkSettings']['IPAddress']
        logger.info(f"Validator container IP: {container_ip}")

        # Check connectivity
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        result = s.connect_ex((container_ip, 8000))
        if result == 0:
            logger.info(f"Successfully connected to {container_ip}:8000")
        else:
            logger.error(f"Failed to connect to {container_ip}:8000. Error code: {result}")
        s.close()

        # Send POST request to the validator using the container's IP
        logger.info(f"Sending request to http://{container_ip}:8000")
        response = requests.post(f"http://{container_ip}:8000", json=data, timeout=35)

        if response.status_code != 200:
            logger.error(f"Error processing task: {response.text}")
            return False

        result = response.json()
        logger.info(f"Validation result for {validator_type}: {result}")
        return result['is_valid']

    except requests.exceptions.ConnectTimeout:
        logger.error(f"Connection to {container_ip}:8000 timed out")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
    except socket.gaierror as e:
        logger.error(f"Address-related error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    return False

def cleanup(signum=None, frame=None):
    logger.info("Starting cleanup process")
    for validator_type in list(active_validators.keys()):
        container_name = f'gsc-{validator_type}-proof' if os.environ.get('SGX') == 'true' else f'{validator_type}-proof'
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