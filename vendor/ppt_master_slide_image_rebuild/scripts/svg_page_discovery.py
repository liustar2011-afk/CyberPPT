#!/usr/bin/env python3
"""
Locate the active page SVG under slide-image-rebuild project folders.

When both svg_output/ and svg_final/ exist, prefer the file with the newest
mtime so stale finalized copies do not shadow fresh executor output.
"""

from __future__ import annotations

from pathlib import Path


def _collect_svg_matches(svg_dir: Path, page_id: str) -> list[Path]:
    if not svg_dir.is_dir():
        return []
    matches = sorted(svg_dir.glob(f"{page_id}*.svg"))
    if not matches:
        matches = sorted(svg_dir.glob("*.svg"))
    return [path for path in matches if ".fixture_backup." not in path.name]


def find_page_svg(
    project: Path,
    page_id: str,
    *,
    page_dir: Path | None = None,
) -> Path | None:
    """Return the freshest SVG for a page across svg_output/ and svg_final/."""
    best: Path | None = None
    best_mtime = -1.0
    roots: list[Path] = []
    if page_dir is not None and page_dir.is_dir():
        roots.append(page_dir)
    roots.append(project)

    for root in roots:
        for folder in ("svg_output", "svg_final"):
            for path in _collect_svg_matches(root / folder, page_id):
                mtime = path.stat().st_mtime
                if mtime > best_mtime:
                    best = path
                    best_mtime = mtime
    return best


def list_page_svg_candidates(
    project: Path,
    page_id: str,
    *,
    page_dir: Path | None = None,
) -> list[Path]:
    """Return all matching SVG paths, newest first."""
    candidates: list[Path] = []
    seen: set[str] = set()
    roots: list[Path] = []
    if page_dir is not None and page_dir.is_dir():
        roots.append(page_dir)
    roots.append(project)

    for root in roots:
        for folder in ("svg_output", "svg_final"):
            for path in _collect_svg_matches(root / folder, page_id):
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(path)
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates
