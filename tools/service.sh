#!/bin/bash

# This script can be used by cron to auto start Datalad-Registry service upon
# the host's reboot.

set -eu
umask 077

# Set working directory to the root of the Datalad-Registry repository
cd "$(dirname "$0")" && cd ..

# Load environment variables from .env.typhon
set -a
# shellcheck disable=SC1091
source ./.env.typhon
set +a

# Start the Datalad-Registry with podman-compose
podman-compose -f docker-compose.yml up -d
