"""Read page-level routing data from a CyberPPT Stage 01 outline.

This is intentionally a small, side-effect-free parser.  Prompt generation,
visual routing, and manifest assembly can all consume the same page context
without each module reimplementing JSON loading and field filtering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


OUTLINE_FIELDS = (
    "argument_role",
    "page_job",
    "business_question",
    "visual_center",
    "visual_proof",
    "visual_intent_type",
    "visual_carrier",
    "onscreen_judgment_mode",
    "judgment_role",
)


def outline_path(project: Path) -> Path:
    return project / "workbench" / "stages" / "01-analysis" / "outline.json"


def load_outline_pages(project: Path) -> list[dict[str, Any]]:
    """Return normalized page dictionaries, or an empty list if absent."""

    path = outline_path(project)
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        return []
    return [item for item in pages if isinstance(item, dict) and item.get("page_id")]


def _clean_fields(item: dict[str, Any], fields: Iterable[str]) -> dict[str, str]:
    return {
        field: str(item.get(field) or "").strip()
        for field in fields
        if str(item.get(field) or "").strip()
    }


def load_page_missions(project: Path) -> dict[str, str]:
    """Return ``page_id -> business_question`` for prompt context."""

    return {
        str(item["page_id"]): str(item.get("business_question") or "").strip()
        for item in load_outline_pages(project)
    }


def load_page_visual_contexts(project: Path) -> dict[str, dict[str, str]]:
    """Return the stable visual/judgment context consumed by compilers."""

    return {
        str(item["page_id"]): _clean_fields(item, OUTLINE_FIELDS)
        for item in load_outline_pages(project)
    }


def load_page_visual_intent_overrides(
    project: Path,
    *,
    allowed_fields: Iterable[str],
) -> dict[str, dict[str, str]]:
    """Return only explicitly authored visual-intent override fields."""

    allowed = set(allowed_fields)
    result: dict[str, dict[str, str]] = {}
    for item in load_outline_pages(project):
        raw = item.get("visual_intent")
        if not isinstance(raw, dict):
            continue
        cleaned = {
            key: value.strip()
            for key, value in raw.items()
            if key in allowed and isinstance(value, str) and value.strip()
        }
        if cleaned:
            result[str(item["page_id"])] = cleaned
    return result


def load_page_context_bundle(
    project: Path,
    *,
    allowed_override_fields: Iterable[str],
) -> tuple[dict[str, str], dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Load missions, visual contexts, and overrides in one deterministic read."""

    pages = load_outline_pages(project)
    missions = {
        str(item["page_id"]): str(item.get("business_question") or "").strip()
        for item in pages
    }
    contexts = {
        str(item["page_id"]): _clean_fields(item, OUTLINE_FIELDS)
        for item in pages
    }
    allowed = set(allowed_override_fields)
    overrides: dict[str, dict[str, str]] = {}
    for item in pages:
        raw = item.get("visual_intent")
        if not isinstance(raw, dict):
            continue
        cleaned = {
            key: value.strip()
            for key, value in raw.items()
            if key in allowed and isinstance(value, str) and value.strip()
        }
        if cleaned:
            overrides[str(item["page_id"])] = cleaned
    return missions, contexts, overrides


__all__ = [
    "OUTLINE_FIELDS",
    "load_outline_pages",
    "load_page_context_bundle",
    "load_page_missions",
    "load_page_visual_contexts",
    "load_page_visual_intent_overrides",
    "outline_path",
]
