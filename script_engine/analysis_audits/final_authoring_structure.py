"""Focused AUTHOR source-detail, content-coverage, and topology audit helpers."""
from __future__ import annotations

from .common import *


def _authored_bare_label_detail_issues(
    page: dict[str, Any],
    slide: dict[str, Any],
    items: dict[str, dict[str, Any]],
) -> list[str]:
    """Keep source detail and role-bearing payload attached to visible labels."""

    contract = page.get("onscreen_contract")
    contract = contract if isinstance(contract, dict) else {}
    detail_policy = contract.get("detail_policy")
    detail_policy = detail_policy if isinstance(detail_policy, dict) else {}
    label_only_allowed = detail_policy.get("label_only_allowed") is True
    contract_modules = {
        str(module.get("heading") or "").strip(): module
        for module in contract.get("modules") or []
        if isinstance(module, dict) and str(module.get("heading") or "").strip()
    }
    page_evidence_ids = _page_evidence_ids(page)
    issues: list[str] = []
    for module_index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        heading = str(module.get("heading") or "").strip()
        visible_items = [
            str(value).strip()
            for value in module.get("items") or []
            if isinstance(value, str) and value.strip()
        ]
        if not visible_items:
            continue
        module_contract = contract_modules.get(heading, {})
        evidence_ids = {
            str(value)
            for value in module_contract.get("evidence_refs") or []
            if str(value)
        } or page_evidence_ids
        source_statements = [
            _item_text(items[item_id])
            for item_id in evidence_ids
            if item_id in items
        ]
        collapsed = [
            value
            for value in visible_items
            if (
                is_bare_business_label(value)
                and source_has_richer_item_detail(value, source_statements)
            )
            or label_enumeration_collapses_richer_detail(value, source_statements)
        ]
        role_only = functional_group_needs_item_explanations(
            heading,
            visible_items,
            content_load=page.get("content_load"),
            label_only_allowed=label_only_allowed,
        )
        if collapsed or role_only:
            labels = collapsed or [
                value for value in visible_items if is_bare_business_label(value)
            ]
            issues.append(
                "onscreen module {index} '{heading}' collapses source-backed or role-bearing "
                "details into bare labels {labels}; write '标签：来源支持的对象、作用、任务或边界' "
                "without terminal punctuation. Use detail_policy.label_only_allowed=true only "
                "when the approved source intentionally provides a label-only taxonomy".format(
                    index=module_index,
                    heading=heading or "?",
                    labels=labels,
                )
            )
    return issues


def _audit_authored_content_coverage(page: dict[str, Any], slide: dict[str, Any]) -> list[str]:
    route = page.get("content_route")
    if not isinstance(route, dict):
        return []
    visible = re.sub(r"\s+", "", _slide_text(slide))
    slide_id = str(slide.get("id") or page.get("id") or "?")
    issues: list[str] = []
    for signal in route.get("meaning_signals") or []:
        if isinstance(signal, str) and signal.strip() and re.sub(r"\s+", "", signal) not in visible:
            issues.append(
                f"{slide_id}: content_route meaning signal '{signal}' is absent from final copy"
            )
    return issues


def _authored_relationships_issues(page: dict[str, Any], slide: dict[str, Any]) -> list[str]:
    """Every ``relationships[]`` edge AUTHOR writes must trace to PLAN's approved topology."""

    primary = page.get("primary_relation")
    if not isinstance(primary, dict):
        return []
    scope = {s for s in primary.get("scope") or [] if isinstance(s, str)}
    rel_type = primary.get("type")
    secondary_pairs = {
        (relation.get("from"), relation.get("to"))
        for relation in (page.get("secondary_relations") or [])
        if isinstance(relation, dict)
    }
    hard_topology_allows_scoped_pairs = rel_type in ("sequence", "hierarchy", "matrix", "mixed")

    issues: list[str] = []
    for r_index, relation in enumerate(slide.get("relationships") or []):
        if not isinstance(relation, dict):
            continue
        from_label, to_label = relation.get("from"), relation.get("to")
        pair = (from_label, to_label)
        if pair in secondary_pairs:
            continue
        if hard_topology_allows_scoped_pairs and from_label in scope and to_label in scope:
            continue
        if not scope and not secondary_pairs:
            continue
        issues.append(
            f"relationships[{r_index}] ({from_label} → {to_label}): not declared in plan's "
            "primary_relation topology or secondary_relations; AUTHOR cannot invent a relation "
            "edge PLAN did not sanction"
        )
    return issues


def _slide_text(slide: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "subtitle", "mission", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
        value = slide.get(key)
        if isinstance(value, str):
            parts.append(value)
    argument = slide.get("argument") or {}
    if isinstance(argument, dict):
        if isinstance(argument.get("pattern"), str):
            parts.append(argument["pattern"])
        parts.extend(x for x in (argument.get("chain") or []) if isinstance(x, str))
    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
        for key in ("heading", "text"):
            value = module.get(key)
            if isinstance(value, str):
                parts.append(value)
        parts.extend(x for x in (module.get("items") or []) if isinstance(x, str))
    for relation in slide.get("relationships") or []:
        if not isinstance(relation, dict):
            continue
        for key in ("from", "to", "relation"):
            value = relation.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts)


__all__ = [
    "_authored_bare_label_detail_issues",
    "_audit_authored_content_coverage",
    "_authored_relationships_issues",
    "_slide_text",
]
