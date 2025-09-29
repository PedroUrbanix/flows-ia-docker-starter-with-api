#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/outputs /app/data

echo "flows-ia • starting…"
echo "Python: $(python -V)"
echo "Which python: $(which python)"
echo "Workdir: $(pwd)"

exec "$@"