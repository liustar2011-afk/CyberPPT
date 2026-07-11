#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 0 ]]; then
  echo "usage: $0 (no positional arguments)" >&2
  exit 2
fi

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python interpreter not found: $PYTHON_BIN" >&2
  exit 1
fi
if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
  echo "$PYTHON_BIN must be Python 3.12" >&2
  exit 1
fi

VENV_DIR="$ROOT_DIR/.venv"
"$PYTHON_BIN" -m venv "$VENV_DIR"
VIRTUAL_ENV="$VENV_DIR"
export VIRTUAL_ENV
"$VIRTUAL_ENV/bin/python" -m pip install --upgrade pip
"$VIRTUAL_ENV/bin/python" -m pip install --requirement "$ROOT_DIR/requirements-paddleocr.txt"
echo "PaddleOCR runtime ready at $VENV_DIR"
