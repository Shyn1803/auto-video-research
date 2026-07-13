#!/usr/bin/env sh
set -eu

api_port="${API_PORT:-8000}"
frontend_port="${FRONTEND_PORT:-3000}"

for port in "$api_port" "$frontend_port"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Change API_PORT or FRONTEND_PORT in .env and retry." >&2
    exit 1
  fi
done
