"""Project-level hard gate for Stage 01 faithful AUTHOR execution."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .contracts import load_json
from .source_freshness import (
    build_input_fingerprints,
    canonical_json_sha256,
    packet_freshness,
    utc_now_iso,
)
from .text_io import write_text_lf


AUTHOR_PREFLIGHT_SCHEMA = "cyberppt.author_preflight.v1"
AUTHOR_PREFLIGHT_BUILDER_VERSION = "stage1-author-preflight-v1"
_PAGE_STATUSES = ("passed", "blocked", "missing", "stale", "not_applicable")


def _text(value: object) -> str:
    return str(value or "").strip()


def _source_refs(page: Mapping[str, Any]) -> list[str]:
    return [_text(value) for value in page.get("source_refs") or [] if _text(value)]


def _exact_source_available(packet: Mapping[str, Any]) -> bool:
    evidence = packet.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False
    for item in evidence:
        if not isinstance(item, Mapping):
            return False
        exact_units = item.get("exact_source_units")
        if not isinstance(exact_units, list) or not exact_units:
            return False
        for unit in exact_units:
            if not isinstance(unit, Mapping) or not _text(unit.get("text")):
                return False
    return True


def load_page_source_packets(
    packet_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[str]]:
    """Load persisted packets by page id and report malformed/duplicate artifacts."""

    packets: dict[str, dict[str, Any]] = {}
    paths: dict[str, str] = {}
    issues: list[str] = []
    duplicates: set[str] = set()

    if not packet_dir.is_dir():
        return packets, paths, [f"AUTHOR_PREFLIGHT_PACKET_DIR_MISSING: {packet_dir}"]

    for path in sorted(packet_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(f"AUTHOR_PREFLIGHT_PACKET_INVALID_JSON: {path}: {exc}")
            continue
        if not isinstance(payload, dict):
            issues.append(f"AUTHOR_PREFLIGHT_PACKET_INVALID_OBJECT: {path}")
            continue
        page_id = _text(payload.get("page_id"))
        if not page_id:
            issues.append(f"AUTHOR_PREFLIGHT_PACKET_PAGE_ID_MISSING: {path}")
            continue
        if page_id in packets:
            duplicates.add(page_id)
            issues.append(f"AUTHOR_PREFLIGHT_PACKET_DUPLICATE: {page_id}")
            continue
        packets[page_id] = payload
        paths[page_id] = str(path.resolve())

    for page_id in duplicates:
        packets.pop(page_id, None)
        paths.pop(page_id, None)

    return packets, paths, issues


def build_author_preflight(
    deck_plan: Mapping[str, Any],
    foundation: Mapping[str, Any],
    source_index: Mapping[str, Any],
    packets_by_page: Mapping[str, Mapping[str, Any]],
    *,
    packet_paths: Mapping[str, str] | None = None,
    loader_issues: list[str] | None = None,
) -> dict[str, Any]:
    """Build a deterministic per-page gate summary for AUTHOR.

    Pages without source refs are structural and therefore ``not_applicable``.
    Every page with source refs must have one fresh, passed v2 Page Source Packet
    whose page id, authoring mode, source refs, and exact evidence all agree with
    the current upstream inputs.
    """

    authoring_mode = _text(deck_plan.get("authoring_mode")) or "faithful"
    current_inputs = build_input_fingerprints(deck_plan, foundation, source_index)
    paths = packet_paths or {}
    global_issues = list(loader_issues or [])
    page_results: list[dict[str, Any]] = []

    for page in deck_plan.get("pages") or []:
        if not isinstance(page, Mapping):
            global_issues.append("AUTHOR_PREFLIGHT_PLAN_PAGE_INVALID: page entry is not an object")
            continue

        page_id = _text(page.get("id"))
        refs = _source_refs(page)
        result: dict[str, Any] = {
            "page_id": page_id,
            "page_role": _text(page.get("page_role")),
            "source_refs": refs,
            "gate_status": "not_applicable" if not refs else "missing",
            "freshness": "not_applicable" if not refs else "missing",
            "exact_source_status": "not_applicable" if not refs else "unavailable",
            "issues": [],
        }

        if not page_id:
            result["gate_status"] = "blocked"
            result["freshness"] = "invalid"
            result["issues"].append("AUTHOR_PREFLIGHT_PAGE_ID_MISSING")
            page_results.append(result)
            continue

        if not refs:
            page_results.append(result)
            continue

        packet = packets_by_page.get(page_id)
        if not isinstance(packet, Mapping):
            result["issues"].append("AUTHOR_PREFLIGHT_PACKET_MISSING")
            page_results.append(result)
            continue

        if page_id in paths:
            result["packet_path"] = paths[page_id]
        result["packet_sha256"] = canonical_json_sha256(packet)

        freshness = packet_freshness(packet, deck_plan, foundation, source_index)
        result["freshness"] = freshness
        if freshness == "stale":
            result["gate_status"] = "stale"
            result["issues"].append("AUTHOR_PREFLIGHT_PACKET_STALE")
            page_results.append(result)
            continue
        if freshness == "invalid":
            result["gate_status"] = "blocked"
            result["issues"].append("AUTHOR_PREFLIGHT_PACKET_INVALID")
            page_results.append(result)
            continue

        if _text(packet.get("page_id")) != page_id:
            result["gate_status"] = "blocked"
            result["issues"].append("AUTHOR_PREFLIGHT_PAGE_ID_MISMATCH")
        if _text(packet.get("authoring_mode")) != authoring_mode:
            result["gate_status"] = "blocked"
            result["issues"].append("AUTHOR_PREFLIGHT_AUTHORING_MODE_MISMATCH")
        packet_refs = [_text(value) for value in packet.get("page_source_refs") or [] if _text(value)]
        if packet_refs != refs:
            result["gate_status"] = "blocked"
            result["issues"].append("AUTHOR_PREFLIGHT_SOURCE_REFS_MISMATCH")
        if _text(packet.get("status")) != "passed":
            result["gate_status"] = "blocked"
            result["issues"].append("AUTHOR_PREFLIGHT_PACKET_BLOCKED")

        if _exact_source_available(packet):
            result["exact_source_status"] = "available"
        else:
            result["gate_status"] = "blocked"
            result["exact_source_status"] = "unavailable"
            result["issues"].append("AUTHOR_PREFLIGHT_EXACT_SOURCE_UNAVAILABLE")

        if not result["issues"]:
            result["gate_status"] = "passed"
        page_results.append(result)

    counts = {status: 0 for status in _PAGE_STATUSES}
    for item in page_results:
        status = item["gate_status"]
        if status in counts:
            counts[status] += 1

    overall_status = "passed"
    if global_issues or any(
        item["gate_status"] in {"blocked", "missing", "stale"}
        for item in page_results
    ):
        overall_status = "blocked"

    return {
        "schema": AUTHOR_PREFLIGHT_SCHEMA,
        "builder_version": AUTHOR_PREFLIGHT_BUILDER_VERSION,
        "generated_at": utc_now_iso(),
        "authoring_mode": authoring_mode,
        "inputs": current_inputs,
        "pages": page_results,
        "summary": {
            **counts,
            "overall_status": overall_status,
        },
        "issues": global_issues,
    }


def author_preflight_report(
    plan_path: Path,
    foundation_path: Path,
    *,
    source_index_path: Path | None = None,
    packet_dir: Path | None = None,
    output_path: Path | None = None,
) -> tuple[dict[str, Any], int]:
    """Load project artifacts, build the preflight manifest and optionally persist it."""

    plan = load_json(plan_path)
    foundation = load_json(foundation_path)
    resolved_source_index = (
        source_index_path or foundation_path.parent / ".cache" / "source-index.json"
    )
    if not resolved_source_index.is_file():
        return (
            {
                "schema": "cyberppt.author_preflight_error.v1",
                "status": "blocked",
                "issues": [
                    f"AUTHOR_PREFLIGHT_SOURCE_INDEX_MISSING: {resolved_source_index}"
                ],
            },
            1,
        )

    source_index = load_json(resolved_source_index)
    if source_index.get("schema") != "cyberppt.source_index.v2":
        return (
            {
                "schema": "cyberppt.author_preflight_error.v1",
                "status": "blocked",
                "issues": [
                    "AUTHOR_PREFLIGHT_SOURCE_INDEX_SCHEMA_INVALID: expected cyberppt.source_index.v2"
                ],
            },
            1,
        )

    resolved_packet_dir = packet_dir or foundation_path.parent / ".cache" / "page-source"
    packets, packet_paths, loader_issues = load_page_source_packets(resolved_packet_dir)
    manifest = build_author_preflight(
        plan,
        foundation,
        source_index,
        packets,
        packet_paths=packet_paths,
        loader_issues=loader_issues,
    )

    if output_path is not None:
        output_path = output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_text_lf(output_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    return manifest, 0 if manifest["summary"]["overall_status"] == "passed" else 1


__all__ = [
    "AUTHOR_PREFLIGHT_BUILDER_VERSION",
    "AUTHOR_PREFLIGHT_SCHEMA",
    "author_preflight_report",
    "build_author_preflight",
    "load_page_source_packets",
]
