#!/usr/bin/env bash
# Regenerate requirements.txt and requirements-dev.txt from the .in files.
# Run this after editing a .in file, then commit all four files.
#   ./scripts/lock.sh
#
# The generated files pin every package (including sub-dependencies) to an exact
# version AND a cryptographic hash. pip refuses to install a file whose hash does not
# match, so a tampered or swapped package on PyPI cannot reach production.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v uv >/dev/null || { echo "Install uv first:  pip install uv"; exit 1; }

# --python-version 3.12: what production runs.  --universal: also valid on macOS/Linux, Python 3.13.
COMMON=(--generate-hashes --universal --python-version 3.12 --quiet)

uv pip compile requirements.in     -o requirements.txt     "${COMMON[@]}"
uv pip compile requirements-dev.in -o requirements-dev.txt "${COMMON[@]}"
echo "Locked: requirements.txt, requirements-dev.txt"