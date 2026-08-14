"""Read-only QA and artifact resolution helpers for template rebuilds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cyberppt.artifact_ledger import sha256_path


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def resolve_exported_pptx(project_path: Path, explicit: Path | None = None) -> str | None:
    """Resolve the artifact recorded by this build, never an mtime guess."""

    if explicit is not None:
        candidate = explicit.expanduser().resolve()
        return str(candidate) if candidate.is_file() else None
    pointer = project_path / "analysis" / "export_artifact.json"
    if not pointer.is_file():
        return None
    try:
        payload = read_json_object(pointer)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    raw_path = payload.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    candidate = Path(raw_path).expanduser().resolve()
    if not candidate.is_file():
        return None
    expected_hash = str(payload.get("sha256") or "").lower()
    actual_hash = str(sha256_path(candidate) or "").lower()
    return str(candidate) if not expected_hash or expected_hash == actual_hash else None


def template_gate(
    project_path: Path,
    *,
    export_requested: bool,
    exported_pptx: str | None,
) -> dict[str, Any]:
    checks = {
        "spec_lock_available": (project_path / "spec_lock.md").is_file(),
        "brand_rules_available": (project_path / "templates" / "brand_rules.json").is_file(),
        "master_chrome_available": (project_path / "templates" / "master_elements.svg").is_file(),
        "svg_output_available": any((project_path / "svg_output").glob("*.svg")),
        "pptx_exported": bool(exported_pptx) if export_requested else True,
    }
    return {
        "schema": "cyberppt.dual_image.template_gate.v1",
        "valid": all(checks.values()),
        "checks": checks,
        "export_requested": export_requested,
        "exported_pptx": exported_pptx,
    }


def load_scene_graph_gates(project_path: Path) -> list[dict[str, Any]]:
    return [
        read_json_object(path)
        for path in sorted((project_path / "analysis" / "scene_graph_gate").glob("page_*_scene_graph_gate.json"))
    ]


def load_optional_gate(project_path: Path, relative_path: str) -> dict[str, Any] | None:
    path = project_path / "analysis" / relative_path
    return read_json_object(path) if path.exists() else None


def expected_texts_from_workspace_assignment(workspace_assignment: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for page in workspace_assignment.get("pages", []):
        if not isinstance(page, dict):
            continue
        for item in page.get("assignments", []):
            if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
                texts.append(item["text"])
    return texts


def quality_rules(path: Path) -> list[dict[str, Any]]:
    payload = read_json_object(path)
    rules = payload.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError(f"Quality rules must be a list: {path}")
    return [rule for rule in rules if isinstance(rule, dict)]


def scene_graph_visual_elements(value: Any) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if any(key in value for key in ("bbox", "blueprint_bbox_px", "render_bbox_px", "ppt_target_bbox_px")):
            element = {
                key: item
                for key, item in value.items()
                if key in {"id", "element_id", "element_type", "type", "kind", "role", "bbox", "blueprint_bbox_px", "render_bbox_px", "ppt_target_bbox_px"}
            }
            element.setdefault("element_type", value.get("element_type") or value.get("type") or value.get("kind") or value.get("role") or "visual")
            element.setdefault("source", {"kind": "scene_graph"})
            elements.append(element)
        for child in value.values():
            elements.extend(scene_graph_visual_elements(child))
    elif isinstance(value, list):
        for child in value:
            elements.extend(scene_graph_visual_elements(child))
    return elements


__all__ = [
    "expected_texts_from_workspace_assignment",
    "load_optional_gate",
    "load_scene_graph_gates",
    "quality_rules",
    "read_json_object",
    "resolve_exported_pptx",
    "scene_graph_visual_elements",
    "template_gate",
]
