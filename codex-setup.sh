#!/usr/bin/env bash
# Codex Cloud — setup script.
#
# Paste this into the environment's "Setup script" field.
# This phase HAS internet. The agent phase that follows does NOT, so anything
# that needs downloading must be downloaded here.
#
# Result is cached for ~12h and reused across tasks, so the slow parts only
# hurt once per day.

set -euo pipefail

echo "=== 1. Python 3.12 (arc-agi requires exactly this) ==="
if ! command -v python3.12 >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq python3.12 python3.12-venv python3.12-dev
fi
python3.12 --version

echo "=== 2. Starter kit dependencies ==="
# `make setup` builds .venv, installs arc-agi + kaggle CLI, clones the framework
make setup

echo "=== 3. Warm the game cache — CRITICAL ==="
# Games are fetched from the ARC-AGI API on first run and cached under
# environment_files/. The agent phase is offline, so if we skip this every
# later run dies with "Could not create environment".
make verify-local || echo "WARN: verify-local failed; check the cache below"

echo "=== 4. Confirm the cache is populated ==="
if [ -d environment_files ] && [ "$(ls -A environment_files 2>/dev/null)" ]; then
  echo "cached games:"
  ls environment_files | head -30
  du -sh environment_files
else
  echo "FATAL: environment_files is empty. The agent phase will not be able to"
  echo "play any game. Do not proceed until this directory has content."
  exit 1
fi

echo "=== 5. Pre-create results dir and verify the harness imports ==="
mkdir -p research/results
PYTHONPATH=. .venv/bin/python -c "
from research import compat
compat.report()
from research.strategies import base
print('strategies:', base.available())
"

echo "=== 6. Make PYTHONPATH persist into the agent phase ==="
# Env vars exported here do NOT survive into the agent phase. ~/.bashrc does.
echo "export PYTHONPATH=/workspace/\$(basename \$PWD):\$PYTHONPATH" >> ~/.bashrc

echo "=== setup complete ==="
