#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
WITH_OCR=0

if [[ "${1:-}" == "--ocr" ]]; then
  WITH_OCR=1
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--ocr]" >&2
  exit 2
fi

"$PYTHON_BIN" -m venv "$ROOT/.venv"
VENV_PY="$ROOT/.venv/bin/python"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install 'markitdown[all]'
if [[ "$WITH_OCR" -eq 1 ]]; then
  "$VENV_PY" -m pip install markitdown-ocr openai
fi

"$VENV_PY" "$ROOT/scripts/convert.py" --help >/dev/null
printf 'Installed source-to-markdown runtime in %s\n' "$ROOT/.venv"
