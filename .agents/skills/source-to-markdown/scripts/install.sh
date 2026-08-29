#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
EXTRA=""
case "${1:-}" in
  "") ;;
  --ocr)
    [[ $# -eq 1 ]] || { echo "Usage: $0 [--extra pdf|pptx|xlsx|ocr]" >&2; exit 2; }
    EXTRA="ocr"
    ;;
  --extra)
    [[ $# -eq 2 ]] || { echo "Usage: $0 [--extra pdf|pptx|xlsx|ocr]" >&2; exit 2; }
    EXTRA="$2"
    ;;
  *)
    echo "Usage: $0 [--extra pdf|pptx|xlsx|ocr]" >&2
    exit 2
    ;;
esac
if [[ -n "$EXTRA" && "$EXTRA" != "ocr" && "$EXTRA" != "pdf" && "$EXTRA" != "pptx" && "$EXTRA" != "xlsx" ]]; then
  echo "Usage: $0 [--extra pdf|pptx|xlsx|ocr]" >&2
  exit 2
fi

"$PYTHON_BIN" -m venv "$ROOT/.venv"
VENV_PY="$ROOT/.venv/bin/python"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install markitdown
if [[ "$EXTRA" == "pdf" || "$EXTRA" == "pptx" || "$EXTRA" == "xlsx" ]]; then
  "$VENV_PY" -m pip install "markitdown[$EXTRA]"
elif [[ "$EXTRA" == "ocr" ]]; then
  "$VENV_PY" -m pip install markitdown-ocr openai
fi

"$VENV_PY" "$ROOT/scripts/convert.py" --help >/dev/null
printf 'Installed source-to-markdown runtime in %s\n' "$ROOT/.venv"
