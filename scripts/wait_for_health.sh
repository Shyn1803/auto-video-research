#!/usr/bin/env sh
set -eu

api_port="${API_PORT:-8000}"
for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error "http://localhost:${api_port}/health" >/dev/null; then
    echo "AVR API health check passed."
    exit 0
  fi
  sleep 2
done

echo "AVR API did not become healthy in time." >&2
exit 1
