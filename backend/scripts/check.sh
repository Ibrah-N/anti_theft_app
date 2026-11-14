#!/usr/bin/env bash
# Run every check that CI runs, in the same order. Use before each commit.
#   ./scripts/check.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "── ruff (lint) ──";    ruff check .
echo "── ruff (format) ──";  ruff format --check .
echo "── mypy (types) ──";   mypy
echo "── pytest ──";         ./scripts/test.sh -q