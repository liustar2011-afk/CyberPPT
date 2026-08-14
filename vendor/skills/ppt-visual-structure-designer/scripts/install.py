#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Install ppt-visual-structure-designer skill")
    ap.add_argument("--scope", choices=["user", "repo", "legacy-codex", "custom"], default="user")
    ap.add_argument("--target", help="Required for custom scope")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    source = Path(__file__).resolve().parents[1]
    if args.scope == "user":
        root = Path.home() / ".agents" / "skills"
    elif args.scope == "repo":
        root = Path.cwd() / ".agents" / "skills"
    elif args.scope == "legacy-codex":
        root = Path.home() / ".codex" / "skills"
    else:
        if not args.target:
            raise SystemExit("--target is required for custom scope")
        root = Path(args.target).expanduser().resolve()

    target = root / source.name
    root.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not args.force:
            raise SystemExit(f"Target exists: {target}; use --force to replace")
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"Installed to {target}")
    print("Restart Codex, then invoke: $ppt-visual-structure-designer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
