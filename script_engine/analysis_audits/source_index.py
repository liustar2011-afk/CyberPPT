"""Source Index audit rules."""
from __future__ import annotations

from .common import *

def validate_source_index_coverage(final_script: dict[str, Any], source_index: dict[str, Any]) -> list[str]:
    if source_index.get("schema") == "cyberppt.source_index.v2":
        refs = {
            str(item.get("unit_id")): item
            for item in source_index.get("units") or []
            if isinstance(item, dict) and item.get("unit_id")
        }
    else:
        refs = source_index.get("refs") or {}
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        for ref in slide.get("source_refs") or []:
            if source_index.get("schema") == "cyberppt.source_index.v2" and not str(ref).startswith("SU-"):
                continue
            if isinstance(ref, str) and ref and ref not in refs:
                issues.append(f"slides.{index} ({slide_id}).source_refs: '{ref}' is not mapped in source-index.json")
    return issues

__all__ = ['validate_source_index_coverage']
