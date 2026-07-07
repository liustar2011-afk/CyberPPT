#!/usr/bin/env python3
"""Selectively clear a dual-image project's rebuild artifacts before a rerun.

`rm -rf project/analysis` (and similar wholesale deletes) is the wrong default
habit: `analysis/ocr/` holds the cached vision-OCR result for each page, and
`_layout_for_page` already reuses it unless `--force-ocr` is passed. Nuking it
before every rerun throws away that cache and forces an unnecessary, slow,
non-deterministic network OCR call even when the only thing that changed was
downstream Python logic (workspace assignment, semantic binding, etc.) or pure
script wording that doesn't affect the image itself.

This script clears exactly the stage directories that need a fresh run, and
preserves `analysis/ocr/` by default so OCR-independent iterations (code
changes, script content tweaks) stay fast.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


# Directories safe to wipe on every rerun: derived analysis, generated svg/notes,
# and export output. `analysis/ocr` is deliberately excluded from this default
# list -- it is the one directory whose regeneration costs a real network call.
DEFAULT_CLEAR_DIRS = (
    "analysis/semantic_plan",
    "analysis/semantic_plan_gate",
    "analysis/semantic_containers",
    "analysis/semantic_layout_plan",
    "analysis/semantic_binding",
    "analysis/container_workspace",
    "analysis/workspace_assignment",
    "analysis/structure_inference",
    "analysis/scene_graph",
    "analysis/scene_graph_gate",
    "analysis/page_layout_plan",
    "analysis/page_understanding",
    "analysis/visual_registry",
    "svg_output",
    "notes",
    "exports",
)
ANALYSIS_ROOT_FILES = (
    "analysis/source_capture.json",
    "analysis/source_capture_gate.json",
    "analysis/template_gate.json",
    "analysis/workspace_layout_qa.json",
    "analysis/preflight_gate.json",
    "analysis/build_gate.json",
    "analysis/postflight_gate.json",
    "analysis/page_quality_report.json",
    "analysis/rebuild_quality.json",
    "analysis/template_rebuild_readiness.json",
)
OCR_DIR = "analysis/ocr"


def clear_stale_bytecode_cache(*, dry_run: bool = False) -> list[str]:
    """Remove `__pycache__` under this package's source tree.

    A real, observed failure mode during this pipeline's development: editing
    a module (e.g. a canvas-size constant, or a workspace-assignment fix) and
    re-running `template_rebuild.py` in a fresh `python3` process picked up a
    stale compiled `.pyc` from *before* the edit, silently reproducing the old
    (buggy) behavior with no error. Unlike the project's own `analysis/`
    cache, this is source-tree bytecode cache and is always safe to drop.
    """
    package_dir = Path(__file__).resolve().parent
    removed: list[str] = []
    for cache_dir in package_dir.rglob("__pycache__"):
        removed.append(str(cache_dir))
        if not dry_run:
            shutil.rmtree(cache_dir, ignore_errors=True)
    return removed


def clean_stage(project_path: Path, *, keep_ocr: bool = True, dry_run: bool = False) -> list[str]:
    """Clear rebuild-derived directories in a project, keeping OCR cache by default."""
    removed: list[str] = []
    targets = list(DEFAULT_CLEAR_DIRS)
    if not keep_ocr:
        targets.append(OCR_DIR)
    for relative in targets:
        target = project_path / relative
        if target.exists():
            removed.append(str(target))
            if not dry_run:
                shutil.rmtree(target)
        if not dry_run:
            target.mkdir(parents=True, exist_ok=True)
    for relative in ANALYSIS_ROOT_FILES:
        target = project_path / relative
        if target.is_file():
            removed.append(str(target))
            if not dry_run:
                target.unlink()
    return removed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_path", type=Path, help="Project directory (the one holding analysis/, exports/, etc.)")
    parser.add_argument(
        "--fresh-ocr",
        action="store_true",
        help="Also clear analysis/ocr/, forcing a real vision OCR call on the next rebuild. "
        "Only use this when the full/background source images themselves changed.",
    )
    parser.add_argument("--dry-run", action="store_true", help="List what would be removed without deleting anything.")
    parser.add_argument(
        "--keep-bytecode-cache",
        action="store_true",
        help="Skip clearing scripts/dual_image_overlay/**/__pycache__. On by default because stale "
        "bytecode has silently reproduced pre-edit behavior in this pipeline before.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_path = args.project_path.expanduser().resolve()
    if not project_path.is_dir():
        print(f"Error: not a directory: {project_path}", file=sys.stderr)
        return 1
    if not args.keep_bytecode_cache:
        cache_removed = clear_stale_bytecode_cache(dry_run=args.dry_run)
        verb = "Would remove" if args.dry_run else "Removed"
        for path in cache_removed:
            print(f"{verb} (bytecode cache): {path}")
    removed = clean_stage(project_path, keep_ocr=not args.fresh_ocr, dry_run=args.dry_run)
    verb = "Would remove" if args.dry_run else "Removed"
    for path in removed:
        print(f"{verb}: {path}")
    if not removed:
        print("Nothing to clean.")
    if not args.fresh_ocr:
        ocr_dir = project_path / OCR_DIR
        cached = sorted(ocr_dir.glob("*.json")) if ocr_dir.is_dir() else []
        print(f"Kept OCR cache: {len(cached)} file(s) in {ocr_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
