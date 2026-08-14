#!/usr/bin/env bash
set -euo pipefail
SCOPE="${1:-user}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
case "$SCOPE" in
  user) TARGET="$HOME/.agents/skills/word-to-ppt-script" ;;
  repo) TARGET="$(pwd)/.agents/skills/word-to-ppt-script" ;;
  legacy-codex) TARGET="$HOME/.codex/skills/word-to-ppt-script" ;;
  *) echo "usage: $0 [user|repo|legacy-codex]" >&2; exit 2 ;;
esac
rm -rf "$TARGET"
mkdir -p "$(dirname "$TARGET")"
cp -R "$ROOT" "$TARGET"
rm -rf "$TARGET/tests" "$TARGET/__pycache__"
find "$TARGET" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
echo "$TARGET"
