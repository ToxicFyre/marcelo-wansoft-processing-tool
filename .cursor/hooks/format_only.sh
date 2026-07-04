#!/usr/bin/env bash
set -euo pipefail

# Hook JSON on stdin is unused; detach so manual/agent runs never block
exec 0</dev/null

# Use python -m so ruff runs from project venv (works when ruff not on PATH)
cd "${CURSOR_PROJECT_DIR:-.}"

PY="${PY:-}"
if [ -z "$PY" ]; then
  if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PY=python3
  else
    PY=python
  fi
fi

"$PY" -m ruff format .