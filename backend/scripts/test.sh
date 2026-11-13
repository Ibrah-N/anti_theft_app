#!/usr/bin/env bash
# Run the backend test suite against throwaway Docker services.
#
#   ./scripts/test.sh                 # whole suite
#   ./scripts/test.sh tests/test_auth.py -k login    # any pytest arguments
#   KEEP=1 ./scripts/test.sh          # leave the services running afterwards
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE=(docker compose -f docker-compose.test.yml)

"${COMPOSE[@]}" up -d --wait

cleanup() {
  if [[ "${KEEP:-0}" != "1" ]]; then
    "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null
  fi
}
trap cleanup EXIT

python -m pytest "$@"