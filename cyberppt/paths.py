"""Repository path helpers for CyberPPT CLI commands."""

from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
ASSETS_DIR = REPO_ROOT / "assets"
REFERENCES_DIR = REPO_ROOT / "references"
WORKFLOW_FILE = REPO_ROOT / "docs" / "CYBERPPT_WORKFLOW.md"


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)
