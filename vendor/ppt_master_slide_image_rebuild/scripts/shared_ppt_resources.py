#!/usr/bin/env python3
"""
PPT Master - Shared Resource Resolver

Resolve ppt-master resources for slide-image-rebuild without hardcoding one
machine path. The local skill keeps its strict rebuild/export gates, while
shared assets and tools come from the host ppt-master repository when present.

Usage:
    python3 scripts/shared_ppt_resources.py --json
    python3 scripts/shared_ppt_resources.py icons_dir

Examples:
    python3 scripts/shared_ppt_resources.py svg_quality_checker

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
SLIDE_REBUILD_ROOT = _SCRIPTS_DIR.parent
BINDINGS_PATH = SLIDE_REBUILD_ROOT / "resource_bindings.json"


def _load_bindings() -> dict[str, Any]:
    try:
        return json.loads(BINDINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "prefer_ppt_master_resources": True,
            "shared": {},
            "local_fallback": {},
        }


def _candidate_repo_roots() -> list[Path]:
    candidates: list[Path] = []
    env_root = os.environ.get("PPT_MASTER_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root).expanduser())
    for parent in [SLIDE_REBUILD_ROOT, *SLIDE_REBUILD_ROOT.parents]:
        candidates.append(parent)
    out: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            out.append(resolved)
    return out


def ppt_master_repo_root() -> Path | None:
    for candidate in _candidate_repo_roots():
        if (candidate / "skills" / "ppt-master" / "SKILL.md").is_file():
            return candidate
    return None


def local_path(key: str) -> Path | None:
    bindings = _load_bindings()
    fallback = bindings.get("local_fallback", {})
    if not isinstance(fallback, dict):
        return None
    raw = fallback.get(key)
    if not isinstance(raw, str) or not raw:
        return None
    return (SLIDE_REBUILD_ROOT / raw).resolve()


def shared_path(key: str) -> Path | None:
    bindings = _load_bindings()
    if bindings.get("prefer_ppt_master_resources") is False:
        return None
    shared = bindings.get("shared", {})
    if not isinstance(shared, dict):
        return None
    raw = shared.get(key)
    if not isinstance(raw, str) or not raw:
        return None
    repo = ppt_master_repo_root()
    if repo is None:
        return None
    candidate = (repo / raw).resolve()
    return candidate if candidate.exists() else None


def resource_path(key: str) -> Path:
    shared = shared_path(key)
    if shared is not None:
        return shared
    local = local_path(key)
    if local is not None and local.exists():
        return local
    repo = ppt_master_repo_root()
    searched = []
    if repo is not None:
        searched.append(str(repo))
    searched.append(str(SLIDE_REBUILD_ROOT))
    raise FileNotFoundError(f"Resource `{key}` not found. Searched: {', '.join(searched)}")


def icons_dir() -> Path:
    return resource_path("icons_dir")


def svg_quality_checker_script() -> Path:
    return resource_path("svg_quality_checker")


def svg_editor_server_script() -> Path:
    return resource_path("svg_editor_server")


def resource_report() -> dict[str, Any]:
    keys = [
        "skill_dir",
        "icons_dir",
        "templates_dir",
        "charts_dir",
        "layouts_dir",
        "brands_dir",
        "references_dir",
        "workflows_dir",
        "svg_quality_checker",
        "svg_editor_server",
        "officecli_dir",
    ]
    repo = ppt_master_repo_root()
    resolved: dict[str, dict[str, Any]] = {}
    for key in keys:
        shared = shared_path(key)
        fallback = local_path(key)
        chosen: Path | None = shared
        source = "shared"
        if chosen is None and fallback is not None and fallback.exists():
            chosen = fallback
            source = "local_fallback"
        resolved[key] = {
            "path": str(chosen) if chosen else None,
            "exists": bool(chosen and chosen.exists()),
            "source": source if chosen else "missing",
        }
    return {
        "valid": True,
        "slide_image_rebuild_root": str(SLIDE_REBUILD_ROOT),
        "ppt_master_repo_root": str(repo) if repo else None,
        "bindings": str(BINDINGS_PATH),
        "resources": resolved,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve shared ppt-master resources for slide-image-rebuild.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("key", nargs="?", help="Resource key to print")
    parser.add_argument("--json", action="store_true", help="Print the full resource report as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.json or not args.key:
        print(json.dumps(resource_report(), ensure_ascii=False, indent=2))
        return 0
    try:
        print(resource_path(args.key))
    except FileNotFoundError as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
