"""Project-directory scaffolding for the standalone Script Engine workflow."""
from __future__ import annotations

import re
from pathlib import Path


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Directories a downstream pipeline (e.g. CyberPPT Stage 02) may write into
# this project folder. They are not authoritative Script Engine artifacts.
PROJECT_GITIGNORE = """# Non-authoritative artifacts produced by downstream pipelines (Stage 02 and later).
# This repo's only authoritative content is foundation.json, deck-plan.json and dist/final-script.md.
workbench/
outputs/
delivery/
visual/
"""


def create_project(slug: str, base_dir: Path) -> Path:
    """Create a fresh Script Engine project tree and return its directory."""

    if not SLUG_PATTERN.match(slug):
        raise ValueError(
            f"'{slug}' is not a valid project slug: use lowercase letters, digits, and hyphens only"
        )

    project_dir = base_dir / slug
    if project_dir.exists():
        raise FileExistsError(f"project directory already exists: {project_dir}")

    for directory in (project_dir / "dist", project_dir / "sources", project_dir / ".cache"):
        directory.mkdir(parents=True)
    (project_dir / "dist" / ".gitkeep").touch()
    (project_dir / "sources" / ".gitkeep").touch()
    (project_dir / ".gitignore").write_text(PROJECT_GITIGNORE, encoding="utf-8")
    return project_dir


__all__ = ["PROJECT_GITIGNORE", "SLUG_PATTERN", "create_project"]
