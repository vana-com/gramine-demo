#!/bin/sh

# Activate the virtual environment
. /app/venv/bin/activate

# Forward SIGTERM to the Python process
trap 'kill -TERM $PID' TERM INT

# Start the Python application
exec "$@" &

PID=$!
wait $PID
trap - TERM INT
wait $PID
EXIT_STATUS=$?

exit $EXIT_STATUS