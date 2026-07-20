#!/bin/bash

set -eu
umask 077

# Log everything (very important for debugging cron)
exec >> "$HOME/service-falkor.debug.log" 2>&1
echo "=== $(date) starting service-falkor.sh ==="

# Ensure PATH is correct (cron does NOT load your shell config)
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# Go to project root
cd "$(dirname "$0")" && cd ..

echo "Working directory: $(pwd)"

# Load environment variables
set -a
# shellcheck disable=SC1091
source "./.env.read-only.falkor"
set +a

echo "Environment loaded"

# Start service
podman-compose -f docker-compose.read-only.yml up -d

echo "=== $(date) finished ==="
