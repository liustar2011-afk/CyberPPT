"""Critic-priority ranking derived from composed trace and external-risk signals."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .composed_trace_core import trace_composed


def _external_check_page_ids(
    final_script: dict[str, Any], plan: dict[str, Any], foundation: dict[str, Any]
) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    slide_refs = {
        str(slide.get("id")): {
            str(ref) for ref in slide.get("source_refs") or [] if str(ref)
        }
        for slide in final_script.get("slides") or []
        if isinstance(slide, dict) and slide.get("id")
    }
    for page in plan.get("pages") or []:
        if not isinstance(page, dict) or not page.get("id"):
            continue
        checks = page.get("external_claim_checks") or page.get("external_claim_check")
        if checks:
            counts[str(page["id"])] += len(checks) if isinstance(checks, list) else 1
    for check in foundation.get("external_claim_checks") or []:
        if not isinstance(check, dict):
            continue
        page_ids = [check.get("page_id"), *(check.get("page_ids") or [])]
        for page_id in page_ids:
            if page_id:
                counts[str(page_id)] += 1
        refs = {str(ref) for ref in check.get("source_refs") or [] if str(ref)}
        for slide_id, used_refs in slide_refs.items():
            if refs & used_refs:
                counts[slide_id] += 1
    for key in ("facts", "concepts", "entities", "relations", "arguments", "constraints", "numbers"):
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            origin = str(item.get("claim_origin") or "").casefold()
            requires_check = bool(
                origin.startswith("external")
                or item.get("requires_external_verification")
                or item.get("external_claim_check")
            )
            if not requires_check:
                continue
            refs = {str(ref) for ref in item.get("source_refs") or [] if str(ref)}
            for slide_id, used_refs in slide_refs.items():
                if refs & used_refs:
                    counts[slide_id] += 1
    return dict(counts)


def critic_priorities(
    final_script: dict[str, Any],
    plan: dict[str, Any],
    foundation: dict[str, Any],
    *,
    trace: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Focus AUTHOR Critic on high-risk pages without creating a new gate."""

    trace = trace or trace_composed(final_script, foundation)
    reasons: dict[str, set[str]] = defaultdict(set)
    composed_counts: dict[str, int] = defaultdict(int)
    hard_counts: dict[str, int] = defaultdict(int)
    for record in trace.get("composed") or []:
        slide_id = str(record.get("slide_id") or "")
        if slide_id:
            reasons[slide_id].add("composed_lines")
            composed_counts[slide_id] += 1
    for record in trace.get("hard_findings") or []:
        slide_id = str(record.get("slide_id") or "")
        if slide_id:
            reasons[slide_id].add("hard_source_boundary")
            hard_counts[slide_id] += 1
    design = plan.get("narrative_design") if isinstance(plan.get("narrative_design"), dict) else {}
    peak_page_id = str(design.get("peak_page_id") or "")
    if peak_page_id:
        reasons[peak_page_id].add("peak_page")
    external_counts = _external_check_page_ids(final_script, plan, foundation)
    for slide_id, count in external_counts.items():
        if count:
            reasons[slide_id].add("external_claim_checks")
    assets = {
        str(asset.get("id")): asset
        for asset in foundation.get("source_assets") or []
        if isinstance(asset, dict) and asset.get("id")
    }
    for page in plan.get("pages") or []:
        if not isinstance(page, dict):
            continue
        visual = page.get("visual_evidence")
        if not isinstance(visual, dict) or visual.get("kind") != "asset":
            continue
        asset = assets.get(str(visual.get("ref") or "")) or {}
        if asset.get("wrong_reading") or asset.get("presentation_role") == "money_slide":
            reasons[str(page.get("id") or "?")].add("source_asset_wrong_reading")
    slide_order = {
        str(slide.get("id")): index
        for index, slide in enumerate(final_script.get("slides") or [])
        if isinstance(slide, dict) and slide.get("id")
    }
    priorities = [
        {
            "page_id": page_id,
            "reasons": sorted(page_reasons),
            "composed_line_count": composed_counts.get(page_id, 0),
            "hard_finding_count": hard_counts.get(page_id, 0),
            "external_claim_check_count": external_counts.get(page_id, 0),
            "priority_score": (
                100 * hard_counts.get(page_id, 0)
                + (60 if "peak_page" in page_reasons else 0)
                + 40 * external_counts.get(page_id, 0)
                + (30 if "source_asset_wrong_reading" in page_reasons else 0)
                + min(composed_counts.get(page_id, 0), 20)
            ),
        }
        for page_id, page_reasons in reasons.items()
    ]
    priorities.sort(
        key=lambda item: (
            -int(item["priority_score"]),
            slide_order.get(str(item["page_id"]), 10**9),
            str(item["page_id"]),
        )
    )
    return priorities


__all__ = ["critic_priorities"]
