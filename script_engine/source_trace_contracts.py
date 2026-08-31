"""Source-reference traceability checks for Script Engine artifacts."""
from __future__ import annotations

from typing import Any


FOUNDATION_CITABLE_KEYS = (
    "facts",
    "concepts",
    "entities",
    "relations",
    "arguments",
    "constraints",
    "numbers",
)


def collect_foundation_source_codes(foundation: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    for key in FOUNDATION_CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if isinstance(item_id, str) and item_id:
                codes.add(item_id)
            for ref in item.get("source_refs") or []:
                if isinstance(ref, str) and ref:
                    codes.add(ref)
    return codes


def validate_source_refs_coverage(
    final_script: dict[str, Any],
    foundation: dict[str, Any],
) -> list[str]:
    """Require every Final Script source ref to resolve in Foundation."""

    known = collect_foundation_source_codes(foundation)
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        for ref in slide.get("source_refs") or []:
            if isinstance(ref, str) and ref and ref not in known:
                issues.append(
                    f"slides.{index} ({slide_id}).source_refs: '{ref}' "
                    "does not match any citation in foundation.json"
                )
    return issues


__all__ = [
    "FOUNDATION_CITABLE_KEYS",
    "collect_foundation_source_codes",
    "validate_source_refs_coverage",
]
