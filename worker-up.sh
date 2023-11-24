#!/bin/bash

# Default values for parameters
env_file=""
pids_limit=""

# Parse keyword arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --env-file) env_file="$2"; shift ;;
        --pids-limit) pids_limit="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Check if required parameters are provided
if [ -z "$env_file" ] || [ -z "$pids_limit" ]; then
    echo "Usage: $0 --env-file path_to_env_file --pids-limit pids_limit"
    exit 1
fi

# Load environment variables from the provided file
set -a && source "$env_file" && set +a

# Run the podman command with the PID limit
podman run -d \
  --name datalad-registry_worker_1 \
  --network datalad-registry_default \
  --network-alias worker \
  --pids-limit "$pids_limit" \
  -v "${WORKER_PATH_AT_HOST}/data/cache:/data/cache" \
  -e FLASK_APP=datalad_registry:create_app \
  -e DATALAD_REGISTRY_OPERATION_MODE="${DATALAD_REGISTRY_OPERATION_MODE}" \
  -e DATALAD_REGISTRY_INSTANCE_PATH=/app/instance \
  -e DATALAD_REGISTRY_DATASET_CACHE=/data/cache \
  -e CELERY_BROKER_URL="${CELERY_BROKER_URL}" \
  -e CELERY_RESULT_BACKEND=redis://backend:6379 \
  -e SQLALCHEMY_DATABASE_URI="${SQLALCHEMY_DATABASE_URI}" \
  --health-cmd="celery -A datalad_registry.make_celery:celery_app status --timeout 1 --json | grep pong" \
  --health-interval=30s \
  --health-retries=3 \
  --health-start-period=3m \
  --health-timeout=30s \
  datalad-registry:dev \
  bash -c "celery -A datalad_registry.make_celery:celery_app worker --loglevel DEBUG --pool prefork"
