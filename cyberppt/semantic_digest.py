"""Stable semantic digests for Stage 01 authority boundaries.

Raw file hashes remain useful receipts, but must not drive invalidation when
only timestamps, paths, Markdown decoration, or report formatting changes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


VOLATILE_KEYS = {
    "audited_at",
    "approved_at",
    "captured_at",
    "generated_at",
    "prepared_at",
    "reviewed_at",
    "updated_at",
    "created_at",
    "path",
    "input_path",
    "outline_path",
}


def _digest(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _stable_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _stable_json(item)
            for key, item in sorted(value.items())
            if str(key) not in VOLATILE_KEYS
            and str(key) != "sha256"
            and not str(key).endswith("_sha256")
        }
    if isinstance(value, list):
        return [_stable_json(item) for item in value]
    if isinstance(value, str):
        return " ".join(value.split())
    return value


def json_semantic_digest(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return _digest(_stable_json(payload))


def source_truth_semantic_digest(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    authority = {
        "schema": payload.get("schema"),
        "records": payload.get("records", []),
    }
    return _digest(_stable_json(authority))


def outline_semantic_digest(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    authority = {
        "schema": payload.get("schema"),
        "document_semantics": payload.get("document_semantics"),
        "narrative_thesis": payload.get("narrative_thesis"),
        "chapters": payload.get("chapters", []),
        "pages": payload.get("pages", []),
    }
    return _digest(_stable_json(authority))


def _plain_onscreen(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"^\s*#{1,6}\s+", "", raw)
        line = re.sub(r"^\s*[-*+]\s+", "", line)
        line = line.replace("**", "").strip()
        if line:
            lines.append(" ".join(line.split()))
    return "\n".join(lines)


def script_semantic_digest(path: Path) -> str:
    # Local import avoids a module cycle at import time.
    from cyberppt.script_quality_contract import parse_script_path

    document = parse_script_path(path)
    if not document.pages:
        raise ValueError(f"script has no contract pages: {path}")
    if not any(
        page.core_message
        or page.full_prose
        or page.onscreen_text
        or page.speaker_notes
        for page in document.pages
    ):
        raise ValueError(f"script has no semantic contract content: {path}")
    pages = []
    for page in document.pages:
        pages.append(
            {
                "page_id": page.page_id,
                "page_type": page.page_type,
                "title": " ".join(page.title.split()),
                "subtitle": " ".join(page.subtitle.split()),
                "core_message": " ".join(page.core_message.split()),
                "full_prose": " ".join(page.full_prose.split()),
                "selection_notes": " ".join(page.selection_notes.split()),
                "evidence_map": " ".join(page.evidence_map.split()),
                "source_refs": list(page.source_refs),
                "boundary_source_refs": list(page.boundary_source_refs),
                "boundary": " ".join(page.boundary.split()),
                "onscreen_text": _plain_onscreen(page.onscreen_text),
                "visual_structure": " ".join(page.visual_structure.split()),
                "speaker_notes": " ".join(page.speaker_notes.split()),
            }
        )
    return _digest({"schema": "cyberppt.script_semantics.v1", "pages": pages})


def chapter_manifest_semantic_digest(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    reviews = []
    for entry in payload.get("reviews", []):
        if not isinstance(entry, dict):
            continue
        reviews.append(
            {
                "chapter_ids": entry.get("chapter_ids", []),
                "page_ids": entry.get("page_ids", []),
                "status": entry.get("status"),
                "high_priority_open": entry.get("high_priority_open", []),
            }
        )
    authority = {
        "schema": payload.get("schema"),
        "level": payload.get("level"),
        "input_semantic_sha256": payload.get("input_semantic_sha256"),
        "reviews": reviews,
    }
    return _digest(_stable_json(authority))


def stage02_handoff_semantic_digest(path: Path) -> str:
    """Digest the Stage 01 semantic payload consumed by Stage 02.

    File locations, creation time, and raw receipt hashes are intentionally
    excluded by ``_stable_json``.  Page order and every handed-off page field
    remain authoritative.
    """
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    authority = {
        "schema": payload.get("schema"),
        "source_bindings": payload.get("source_bindings", {}),
        "page_order": payload.get("page_order", []),
        "pages": payload.get("pages", []),
    }
    return _digest(_stable_json(authority))
