#!/bin/bash

echo "Current directory:"
pwd

echo "Directory contents:"
ls -R

echo "PYTHONPATH:"
echo $PYTHONPATH

echo "Python version:"
python --version

echo "Pip list:"
pip list

echo "Contents of proof-node directory:"
ls -R /app/proof-node

echo "Starting AESMD service..."
/opt/intel/sgx-aesm-service/aesm/aesm_service --no-daemon &

echo "Attempting to run proof-node module..."
python -m proof-node

echo "If you see this message, the script completed without crashing."