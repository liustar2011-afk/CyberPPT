#!/usr/bin/env bash
# Run a command with the repo .venv Python when present (preview / strict gates).
#
# Usage:
#   scripts/repo_python.sh scripts/check_cairo_backend.py --json
set -euo pipefail
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_repo_root="$(cd "${_script_dir}/.." && pwd)"
_venv_python="${_repo_root}/.venv/bin/python"
if [[ -x "${_venv_python}" ]]; then
  exec "${_venv_python}" "$@"
fi
exec python3 "$@"
