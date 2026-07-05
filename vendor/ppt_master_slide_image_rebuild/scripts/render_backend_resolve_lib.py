"""Resolve preview render backend from project manifest / workflow (R2)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

VALID_EXPLICIT = frozenset({"cairo", "none"})
CJK_RE = re.compile(r"[\u3400-\u9fff]")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _manifest_qa_backend(manifest: dict[str, Any]) -> str | None:
    qa = manifest.get("qa")
    if not isinstance(qa, dict):
        return None
    backend = str(qa.get("preview_render_backend", "")).strip().lower()
    if backend in VALID_EXPLICIT:
        return backend
    return None


def is_slide_image_rebuild_project(project: Path) -> bool:
    return (project / "slide_image_rebuild_manifest.json").is_file()


def is_rebuild2_project(project: Path) -> bool:
    layout = _load_json(project / "layout_reference.json")
    if layout.get("workflow") == "layout-reference-rebuild-2":
        return True
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    return manifest.get("rebuild_mode") in {"vector-hifi", "structure_contract"} or bool(manifest)


def project_has_cjk_svg(project: Path) -> bool:
    for folder in ("svg_output", "svg_final"):
        svg_dir = project / folder
        if not svg_dir.is_dir():
            continue
        for svg in svg_dir.glob("*.svg"):
            try:
                if CJK_RE.search(svg.read_text(encoding="utf-8")):
                    return True
            except OSError:
                continue
    for svg in project.glob("pages/*/svg_output/*.svg"):
        try:
            if CJK_RE.search(svg.read_text(encoding="utf-8")):
                return True
        except OSError:
            continue
    return False


def resolve_project_render_backend(
    project: Path,
    *,
    cli_override: str | None = None,
    hard_gate: bool = False,
) -> tuple[str, list[str]]:
    """
    Choose render backend for similarity / preview gates.

    Priority:
      1. explicit cli_override (not auto)
      2. manifest qa.preview_render_backend
      3. slide-image-rebuild / layout-reference-rebuild-2 / default → cairo
    """
    warnings: list[str] = []
    project = project.resolve()
    override = (cli_override or "").strip().lower()
    if override and override != "auto":
        if hard_gate and override == "auto":
            raise ValueError("hard_gate requires explicit cairo or none.")
        if override not in VALID_EXPLICIT:
            raise ValueError(f"Unknown render backend `{cli_override}`.")
        return override, warnings

    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    qa_backend = _manifest_qa_backend(manifest)
    if qa_backend:
        return qa_backend, warnings

    return "cairo", warnings


def resolve_for_ci(project: Path, *, input_backend: str = "auto") -> str:
    """Resolve backend for GitHub Actions (maps auto → project default)."""
    backend, _warnings = resolve_project_render_backend(
        project,
        cli_override=input_backend,
        hard_gate=False,
    )
    return backend
