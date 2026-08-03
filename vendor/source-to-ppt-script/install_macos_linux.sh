#!/usr/bin/env bash
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="${HOME}/.agents/skills/source-to-ppt-script"
mkdir -p "$(dirname "$DEST_DIR")"
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"
for item in SKILL.md LICENSE.txt agents scripts references assets; do
  cp -R "$SOURCE_DIR/$item" "$DEST_DIR/"
done
printf 'Installed to %s\n' "$DEST_DIR"
printf 'Restart Codex if the skill does not appear immediately.\n'
