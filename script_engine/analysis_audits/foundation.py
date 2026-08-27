"""Foundation audit rules."""
from __future__ import annotations

from .common import *

def audit_foundation_analysis(foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    items = foundation_items_by_id(foundation)
    known_ids = set(items)

    for key in CITABLE_KEYS:
        for index, item in enumerate(foundation.get(key) or []):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id") or f"#{index}"
            text = _item_text(item)
            declared = item.get("visibility")
            if any(marker in text for marker in INTERNAL_MARKERS) and declared == "external_ok":
                issues.append(f"{key}.{index} ({item_id}): source text is explicitly internal ('内部…') but visibility is external_ok")

    for index, relation in enumerate(foundation.get("relations") or []):
        if not isinstance(relation, dict):
            continue
        rel_id = relation.get("id") or f"#{index}"
        support_ids = [x for x in (relation.get("support") or []) if isinstance(x, str)]
        support = _support_items(support_ids, items)
        if relation.get("basis") == "inferred":
            if not support_ids:
                issues.append(f"relations.{index} ({rel_id}): inferred relation requires non-empty support fact IDs")
            unknown = [x for x in support_ids if x not in known_ids]
            if unknown:
                issues.append(f"relations.{index} ({rel_id}): inferred relation cites unknown support IDs {unknown}")
            if not relation.get("confidence"):
                warnings.append(f"relations.{index} ({rel_id}): inferred relation has no confidence level")
        if _has_optionality(support):
            relation_text = _item_text(relation)
            if DEEPENING_RE.search(relation_text) and not INDEPENDENCE_RE.search(relation_text):
                issues.append(f"relations.{index} ({rel_id}): support preserves independent choice + progressive deepening, but relation keeps only the progression")

    for index, argument in enumerate(foundation.get("arguments") or []):
        if not isinstance(argument, dict):
            continue
        arg_id = argument.get("id") or f"#{index}"
        support = _support_items(argument.get("support") or [], items)
        claim = str(argument.get("claim") or "")
        group_issue = _group_strength_issue(claim, support)
        if group_issue:
            issues.append(f"arguments.{index} ({arg_id}): {group_issue}")

    structure = [x for x in (foundation.get("source_structure") or []) if isinstance(x, dict)]
    ids = [x.get("id") for x in structure if x.get("id")]
    if len(ids) != len(set(ids)):
        issues.append("source_structure: duplicate structure IDs")
    orders = [x.get("order") for x in structure if isinstance(x.get("order"), int)]
    if len(orders) != len(set(orders)):
        warnings.append("source_structure: duplicate order values; verify source hierarchy ordering")
    return issues, warnings

__all__ = ['audit_foundation_analysis']
