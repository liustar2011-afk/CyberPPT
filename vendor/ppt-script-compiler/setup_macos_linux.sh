#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if ! command -v codex >/dev/null 2>&1; then
  echo "Codex CLI not found. Install it from: https://developers.openai.com/codex/cli"
fi
if command -v codex >/dev/null 2>&1 && ! codex login status >/dev/null 2>&1; then
  echo "Run 'codex login' and choose Sign in with ChatGPT."
fi
