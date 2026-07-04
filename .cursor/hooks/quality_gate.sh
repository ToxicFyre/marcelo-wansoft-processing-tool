#!/usr/bin/env bash
set -euo pipefail

exec 0</dev/null

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

echo "== ruff format --check =="
"$PY" -m ruff format --check src tests --exclude .venv

echo "== ruff check =="
"$PY" -m ruff check src tests --exclude .venv

echo "== mypy =="
"$PY" -m mypy src

echo "== archbrace =="
"$PY" -m archbrace.cli check src

echo "== pytest =="
"$PY" -m pytest -q
