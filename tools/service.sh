#!/bin/bash

# This script can be used by cron to auto start Datalad-Registry service upon
# the host's reboot.

set -eu
umask 077

# Set working directory to the root of the Datalad-Registry repository
cd $(dirname $0) && cd ..

set -a && . ./.env.typhon && set +a && podman-compose -f docker-compose.yml up -d --build
