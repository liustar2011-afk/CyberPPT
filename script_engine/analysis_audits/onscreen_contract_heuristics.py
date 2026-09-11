"""Legacy lexical review signals excluded from structured onscreen authority."""

from __future__ import annotations

from typing import Any

from cyberppt.semantic_group_review import source_colocation_grouping_mismatch

from .common_primitives import _item_text
from .final_authoring_expression import _evidence_first_item_hierarchy_issues


def onscreen_composition_hierarchy_review_findings(
    page: dict[str, Any],
    slide: dict[str, Any],
) -> list[str]:
    """Keep lead-like first-item detection as review-only.

    Whether a proposition-shaped first item is a synthesized lead or a legitimate
    source-native peer cannot be established by length/predicate patterns.  The
    explicit lead-text policy is enforced by semantic_contract; this helper keeps
    only the historical lexical discovery signal for Critic.
    """

    composition = page.get("onscreen_composition")
    if not isinstance(composition, dict) or composition.get("mode") != "evidence_first":
        return []
    slide_id = str(slide.get("id") or page.get("id") or "?")
    findings: list[str] = []
    for module in slide.get("onscreen") or []:
        if isinstance(module, dict):
            findings.extend(_evidence_first_item_hierarchy_issues(slide_id, module))
    return findings


def onscreen_contract_colocation_review_findings(
    page: dict[str, Any],
    items: dict[str, dict[str, Any]],
) -> list[str]:
    """Keep the historical source-colocation classifier as review-only.

    The classifier depends on Chinese business-word patterns such as institutional
    and action/application vocabulary.  It is useful to Critic but cannot own a
    formal blocker after Phase 3, so compatibility mode surfaces it separately
    from deterministic PLAN contract enforcement.
    """

    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict):
        return []

    findings: list[str] = []
    for module_index, module in enumerate(contract.get("modules") or []):
        if not isinstance(module, dict):
            continue
        heading = str(module.get("heading") or "").strip()
        refs = [
            ref
            for ref in module.get("evidence_refs") or []
            if isinstance(ref, str) and ref in items
        ]
        mismatch = source_colocation_grouping_mismatch(
            heading,
            (
                (ref, _item_text(items[ref]), items[ref].get("source_refs") or [])
                for ref in refs
            ),
        )
        if mismatch:
            findings.append(
                "ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY_REVIEW_REQUIRED: "
                f"onscreen_contract.modules[{module_index}] ({heading or '?'}): "
                "lexical source-grouping classifier sees action/application evidence "
                f"{list(mismatch.action_refs)} and institutional evidence "
                f"{list(mismatch.institution_refs)} under one narrow parent; "
                "confirm the hierarchy against source semantics instead of treating this "
                "word-pattern signal as deterministic proof"
            )
    return findings


__all__ = [
    "onscreen_composition_hierarchy_review_findings",
    "onscreen_contract_colocation_review_findings",
]
