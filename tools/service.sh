#!/bin/bash

set -eu
umask 077

# Check if the path to the Datalad-Registry repo is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <directory-path of Datalad-Registry repo>"
    exit 1
fi

cd "$1"

podman-compose -f docker-compose.dev.yml --env-file .env.dev.typhon up -d --build
disown
