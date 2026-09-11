"""Final Script page lineage projection and validation against Author Preflight."""
from __future__ import annotations

from typing import Any, Mapping


def _text(value: object) -> str:
    return str(value or "").strip()


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def _preflight_pages(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    pages: dict[str, Mapping[str, Any]] = {}
    for item in manifest.get("pages") or []:
        if not isinstance(item, Mapping):
            continue
        page_id = _text(item.get("page_id"))
        if page_id:
            pages[page_id] = item
    return pages


def source_provenance_for_page(
    preflight_manifest: Mapping[str, Any],
    page_id: str,
) -> dict[str, Any]:
    """Project the only valid Final Script lineage payload for one passed page."""

    page = _preflight_pages(preflight_manifest).get(_text(page_id))
    if page is None:
        raise ValueError(f"AUTHOR_PREFLIGHT_PAGE_MISSING: {page_id}")
    if page.get("gate_status") != "passed":
        raise ValueError(f"AUTHOR_PREFLIGHT_PAGE_NOT_PASSED: {page_id}")

    packet_sha256 = _text(page.get("packet_sha256"))
    source_refs = _strings(page.get("source_refs"))
    unit_ids = _strings(page.get("unit_ids"))
    if not packet_sha256 or not source_refs or not unit_ids:
        raise ValueError(f"AUTHOR_PREFLIGHT_LINEAGE_INCOMPLETE: {page_id}")

    return {
        "packet_sha256": packet_sha256,
        "source_refs": source_refs,
        "unit_ids": unit_ids,
    }


def validate_final_source_provenance(
    final_script: Mapping[str, Any],
    preflight_manifest: Mapping[str, Any],
) -> list[str]:
    """Require every content slide to reproduce its exact preflight lineage."""

    issues: list[str] = []
    preflight_pages = _preflight_pages(preflight_manifest)

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, Mapping):
            continue
        page_id = _text(slide.get("id")) or "<unknown>"
        is_content = _text(slide.get("page_type")) == "content"
        provenance = slide.get("source_provenance")

        if not is_content:
            if provenance is not None:
                issues.append(f"FINAL_SOURCE_PROVENANCE_FORBIDDEN: {page_id}")
            continue

        if not isinstance(provenance, Mapping):
            issues.append(f"FINAL_SOURCE_PROVENANCE_MISSING: {page_id}")
            continue

        preflight_page = preflight_pages.get(page_id)
        if preflight_page is None:
            issues.append(f"FINAL_SOURCE_PROVENANCE_PREFLIGHT_PAGE_MISSING: {page_id}")
            continue
        if preflight_page.get("gate_status") != "passed":
            issues.append(f"FINAL_SOURCE_PROVENANCE_PREFLIGHT_PAGE_NOT_PASSED: {page_id}")
            continue

        expected_packet = _text(preflight_page.get("packet_sha256"))
        actual_packet = _text(provenance.get("packet_sha256"))
        if not expected_packet or actual_packet != expected_packet:
            issues.append(f"FINAL_SOURCE_PROVENANCE_PACKET_MISMATCH: {page_id}")

        slide_refs = _strings(slide.get("source_refs"))
        provenance_refs = _strings(provenance.get("source_refs"))
        preflight_refs = _strings(preflight_page.get("source_refs"))
        if provenance_refs != slide_refs:
            issues.append(f"FINAL_SOURCE_PROVENANCE_SLIDE_REFS_MISMATCH: {page_id}")
        if provenance_refs != preflight_refs:
            issues.append(f"FINAL_SOURCE_PROVENANCE_PREFLIGHT_REFS_MISMATCH: {page_id}")

        provenance_units = _strings(provenance.get("unit_ids"))
        preflight_units = _strings(preflight_page.get("unit_ids"))
        if provenance_units != preflight_units:
            issues.append(f"FINAL_SOURCE_PROVENANCE_UNIT_IDS_MISMATCH: {page_id}")

    return list(dict.fromkeys(issues))


__all__ = ["source_provenance_for_page", "validate_final_source_provenance"]
