#!/bin/bash

# This script can be used by cron to auto start Datalad-Registry service upon
# the host's reboot.

set -eu
umask 077

# Check if the path to the Datalad-Registry repo is provided
if [ -z "${1:-}" ]; then
    echo "Usage: $0 <directory-path of Datalad-Registry repo>"
    exit 1
fi

cd "$1"

(set -a && . ./.env.dev.typhon && set +a && podman-compose -f docker-compose.yml up -d --build)
