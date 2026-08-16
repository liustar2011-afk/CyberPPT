"""Official layer-four Outline generator.

This module replaces project-specific Outline scripts.  It creates a
source-locked candidate from the validated semantic foundation and can apply a
complete, explicit authoring spec.  It never invents source facts or silently
turns a candidate into an authored Outline.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any


CONTENT_FIELDS = {
    "audience_question",
    "page_mission",
    "key_judgment",
    "non_substitutable_value",
    "judgment_basis",
    "inference_rationale",
    "argument_role",
    "must_not_include",
    "reserved_for_later",
    "split_risk",
    "split_risk_reason",
    "transition_from_previous",
    "transition_to_next",
    "excluded_from_onscreen",
    "authoring_decisions",
    "evidence_roles",
    "argument_chain",
    "content_strategy",
    "suggested_visual_logic",
    "importance",
    "topic_category",
    "attachment_disposition",
    "judgment_role",
    "subtitle_policy",
}
SOURCE_BOUND_FIELDS = {
    "page_id",
    "order",
    "page_type",
    "template_role",
    "section_id",
    "title_intent",
    "source_heading_ids",
    "primary_source_heading_id",
    "evidence",
}
FACT_ROLE_KEYS = ("claim", "reason", "instance", "boundary", "trace_only")
NON_CONTENT_FACT_TYPES = {
    "metadata",
    "trace",
    "trace_only",
    "attachment",
    "attachment_reference",
    "reference",
    "administrative",
}


def _is_attachment_title(value: Any) -> bool:
    return _text(value).startswith("附件")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _title_without_number(value: Any) -> str:
    text = re.sub(r"[\s　]+", "", _text(value))
    for pattern in (
        r"^[一二三四五六七八九十百]+、",
        r"^[（(][一二三四五六七八九十百\d]+[）)]",
        r"^\d+(?:\.\d+)*[.、]",
    ):
        text = re.sub(pattern, "", text, count=1)
    return text


def _load_inputs(semantic_dir: Path, outline_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = ("normalized-facts.json", "argument-chain.json", "semantic-report.json")
    payloads = {name: _read(semantic_dir / name) for name in required}
    if payloads["semantic-report.json"].get("status") != "ok":
        raise ValueError("semantic-report.json must report status: ok")
    workpack_path = outline_dir / "outline-workpack.json"
    if not workpack_path.is_file():
        raise FileNotFoundError(f"outline workpack does not exist: {workpack_path}")
    workpack = _read(workpack_path)
    if workpack.get("artifact_type") != "ppt_outline_workpack":
        raise ValueError("outline-workpack.json must be a ppt_outline_workpack")
    return payloads["normalized-facts.json"], payloads["argument-chain.json"], payloads["semantic-report.json"], workpack


def _heading_maps(workpack: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str | None]]:
    headings = [item for item in workpack.get("source_heading_outline") or [] if isinstance(item, dict) and item.get("section_id")]
    by_id = {str(item["section_id"]): item for item in headings}
    parents = {str(item["section_id"]): item.get("parent_id") for item in headings}
    return by_id, parents


def _descendants(section_id: str, parents: dict[str, str | None]) -> set[str]:
    result = {section_id}
    changed = True
    while changed:
        changed = False
        for child, parent in parents.items():
            if child not in result and parent in result:
                result.add(child)
                changed = True
    return result


def _nearest_heading_ids(fact: dict[str, Any], headings: list[dict[str, Any]]) -> list[str]:
    ordered = sorted(
        (item for item in headings if item.get("section_id") and item.get("line") is not None),
        key=lambda item: int(item.get("line") or 0),
    )
    result: list[str] = []
    for evidence in fact.get("evidence") or []:
        if not isinstance(evidence, dict) or evidence.get("line_start") is None:
            continue
        candidates = [item for item in ordered if int(item.get("line") or 0) <= int(evidence["line_start"])]
        if candidates:
            value = str(candidates[-1]["section_id"])
            if value not in result:
                result.append(value)
    return result


def _content_heading_ids(headings: list[dict[str, Any]]) -> list[str]:
    level_two = [str(item["section_id"]) for item in headings if int(item.get("level") or 0) == 2]
    roots = [str(item["section_id"]) for item in headings if int(item.get("level") or 0) == 1]
    if not level_two:
        return roots
    parents = {str(item["section_id"]): item.get("parent_id") for item in headings}
    roots_with_children = {str(parent) for parent in parents.values() if parent}
    return level_two + [root for root in roots if root not in roots_with_children]


def _authoring_page_fields(spec: dict[str, Any]) -> dict[str, Any]:
    """Accept both the compact historical spec and the prepared template."""

    nested = spec.get("authoring")
    if isinstance(nested, dict):
        return deepcopy(nested)
    return deepcopy(spec)


def _spec_planning(authoring_spec: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(authoring_spec, dict):
        return {}
    planning = authoring_spec.get("planning")
    return planning if isinstance(planning, dict) else {}


def _attachment_disposition(
    authoring_spec: dict[str, Any] | None,
    heading_id: str,
) -> str:
    if not isinstance(authoring_spec, dict):
        return "trace_only"
    page_spec = (authoring_spec.get("pages") or {}).get(heading_id)
    if not isinstance(page_spec, dict):
        return _text(_spec_planning(authoring_spec).get("default_attachment_disposition")) or "trace_only"
    fields = _authoring_page_fields(page_spec)
    decisions = fields.get("authoring_decisions")
    if isinstance(decisions, dict) and _text(decisions.get("attachment_disposition")):
        return _text(decisions["attachment_disposition"])
    value = _text(fields.get("attachment_disposition"))
    if value:
        return value
    return _text(_spec_planning(authoring_spec).get("default_attachment_disposition")) or "trace_only"


def _selected_content_heading_ids(
    headings: list[dict[str, Any]],
    authoring_spec: dict[str, Any] | None,
) -> list[str]:
    base = _content_heading_ids(headings)
    if not authoring_spec:
        return [
            str(item)
            for item in base
            if not _is_attachment_title(next((h.get("title") for h in headings if str(h.get("section_id")) == str(item)), ""))
        ]
    return [
        str(item)
        for item in base
        if not _is_attachment_title(next((h.get("title") for h in headings if str(h.get("section_id")) == str(item)), ""))
        or _attachment_disposition(authoring_spec, str(item)) in {"main_deck", "appendix"}
    ]


def _argument_node_registry(
    argument: dict[str, Any],
    headings: list[dict[str, Any]],
    content_ids: list[str],
) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for group_name in ("source_chain", "reconstructed_chain"):
        for node in argument.get(group_name) or []:
            if not isinstance(node, dict) or not node.get("node_id"):
                continue
            node_id = str(node["node_id"])
            registry.setdefault(
                node_id,
                {
                    "id": node_id,
                    "source_heading_ids": [str(value) for value in node.get("section_ids") or [] if str(value)],
                    "source_heading": str(next((item.get("title") for item in headings if str(item.get("section_id")) in {str(value) for value in node.get("section_ids") or []}), "") or ""),
                    "normalized_fact_ids": [str(value) for value in node.get("normalized_fact_ids") or [] if str(value)],
                    "argument_role": _text(node.get("argument_role") or node.get("role")) or "other",
                    "argument_weight": _text(node.get("argument_weight")) or "detail",
                    "status": _text(node.get("status")) or "mixed",
                    "evidence_refs": [str(value) for value in node.get("normalized_fact_ids") or [] if str(value)],
                    "projection_only": True,
                },
            )
    for heading_id in content_ids:
        fallback_id = f"ARG-PROJECTION-{heading_id.upper()}"
        registry.setdefault(
            fallback_id,
            {
                "id": fallback_id,
                "source_heading_ids": [heading_id],
                "source_heading": str(next((item.get("title") for item in headings if str(item.get("section_id")) == heading_id), "") or ""),
                "normalized_fact_ids": [],
                "argument_role": "source_exposition",
                "argument_weight": "detail",
                "status": "mixed",
                "evidence_refs": [],
                "projection_only": True,
            },
        )
    return registry


def _page_argument_nodes(
    registry: dict[str, dict[str, Any]],
    heading_ids: list[str],
    fact_ids: set[str],
    primary_heading_id: str,
) -> list[str]:
    result: list[str] = []
    heading_set = set(heading_ids)
    for node_id, node in registry.items():
        node_headings = set(str(value) for value in node.get("source_heading_ids") or [])
        node_facts = set(str(value) for value in node.get("normalized_fact_ids") or [])
        if node_headings.intersection(heading_set) and node_facts.intersection(fact_ids):
            result.append(node_id)
    if not result:
        result.append(f"ARG-PROJECTION-{primary_heading_id.upper()}")
    return result


def _page_graph_evidence(
    facts: list[dict[str, Any]],
    concepts: dict[str, Any],
    relations: dict[str, Any],
) -> tuple[list[str], list[str], str]:
    fact_ids = {str(value) for value in _fact_ids(facts)}
    concept_ids = [
        str(item.get("concept_id"))
        for item in concepts.get("concepts") or []
        if isinstance(item, dict)
        and item.get("concept_id")
        and fact_ids.intersection(str(value) for value in item.get("normalized_fact_ids") or [])
    ]
    relation_ids: list[str] = []
    inference_notes: list[str] = []
    for item in relations.get("relations") or []:
        if not isinstance(item, dict) or not item.get("relation_id"):
            continue
        relation_facts = {str(value) for value in item.get("normalized_fact_ids") or []}
        if relation_facts and relation_facts.issubset(fact_ids):
            relation_ids.append(str(item["relation_id"]))
            if item.get("basis") == "inferred":
                inference_notes.append(_text(item.get("inference_rationale")) or f"沿用推断关系 {item['relation_id']} 的上游说明。")
    return list(dict.fromkeys(concept_ids)), relation_ids, "；".join(inference_notes)


def _content_owner(
    heading_id: str,
    by_id: dict[str, dict[str, Any]],
    parents: dict[str, str | None],
    content_ids: set[str],
) -> str | None:
    current: str | None = heading_id
    while current:
        if current in content_ids:
            return current
        current = parents.get(current)
    if by_id.get(heading_id, {}).get("level") == 1:
        children = [
            str(item["section_id"])
            for item in by_id.values()
            if item.get("parent_id") == heading_id and str(item["section_id"]) in content_ids
        ]
        return children[0] if children else None
    return None


def _fact_role(fact: dict[str, Any], index: int) -> str:
    fact_type = _text(fact.get("fact_type")).lower()
    if index == 0:
        return "claim"
    if fact_type in {"condition", "constraint", "responsibility", "policy_basis"}:
        return "boundary"
    if fact_type in {"service", "dataset", "scenario", "technology", "platform", "deliverable", "metric", "project"}:
        return "instance"
    if fact_type in {"requirement", "process", "goal", "capability", "relationship", "problem"}:
        return "reason"
    return "trace_only"


def _page_facts(
    facts: list[dict[str, Any]],
    page_heading_id: str,
    by_id: dict[str, dict[str, Any]],
    parents: dict[str, str | None],
    content_ids: set[str],
    fallback_heading_id: str,
) -> list[dict[str, Any]]:
    owned = _descendants(page_heading_id, parents)
    result: list[dict[str, Any]] = []
    for fact in facts:
        if _text(fact.get("fact_type")).lower() in NON_CONTENT_FACT_TYPES:
            continue
        nearest = _nearest_heading_ids(fact, list(by_id.values()))
        owners = {
            _content_owner(value, by_id, parents, content_ids)
            for value in nearest
        }
        owners.discard(None)
        if not nearest and page_heading_id == fallback_heading_id:
            owners.add(fallback_heading_id)
        if page_heading_id in owners or any(value in owned for value in nearest):
            result.append(fact)
    return result


def _fact_ids(page_facts: list[dict[str, Any]]) -> list[str]:
    return [str(fact["normalized_fact_id"]) for fact in page_facts if fact.get("normalized_fact_id")]


def _derivation(page_facts: list[dict[str, Any]], judgment: str) -> dict[str, Any]:
    selected = page_facts[:6]
    return {
        "source_refs": _fact_ids(selected),
        "supporting_statements": [_text(fact.get("statement")) for fact in selected],
        "derivation": judgment,
        "introduced_relations": [],
        "introduced_modalities": [],
    }


def _roles(page_facts: list[dict[str, Any]], derivation: dict[str, Any]) -> dict[str, list[str]]:
    roles = {key: [] for key in FACT_ROLE_KEYS}
    claim_ids = {str(value) for value in derivation.get("source_refs") or []}
    for index, fact in enumerate(page_facts):
        fact_id = str(fact.get("normalized_fact_id") or "")
        role = "claim" if fact_id in claim_ids else _fact_role(fact, index)
        if fact_id and fact_id not in roles[role]:
            roles[role].append(fact_id)
    return roles


def _chain(page_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, fact in enumerate(page_facts):
        fact_id = str(fact.get("normalized_fact_id") or "")
        statement = _text(fact.get("statement"))
        if not fact_id or not statement:
            continue
        fact_type = _text(fact.get("fact_type")).lower()
        role = "claim" if index == 0 else "boundary" if fact_type in {"condition", "constraint"} else "response" if fact_type in {"process", "goal", "requirement"} else "support"
        result.append({"role": role, "statement": statement, "evidence": {"normalized_fact_ids": [fact_id]}})
    return result


def _source_argument_chain(
    page_heading_id: str,
    page_facts: list[dict[str, Any]],
    argument: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    parents: dict[str, str | None],
    content_ids: set[str],
) -> list[dict[str, Any]]:
    """Prefer source-chain nodes, but reject heading-only inventory nodes."""
    page_fact_ids = set(_fact_ids(page_facts))
    role_map = {
        "context": "premise",
        "approach": "mechanism",
        "capability": "support",
        "goal": "judgment",
        "process": "response",
        "problem": "gap",
        "constraint": "boundary",
        "requirement": "driver",
    }
    result: list[dict[str, Any]] = []
    for node in sorted(
        (item for item in argument.get("source_chain") or [] if isinstance(item, dict)),
        key=lambda item: int(item.get("order") or 0),
    ):
        owners = {
            _content_owner(str(section_id), by_id, parents, content_ids)
            for section_id in node.get("section_ids") or []
        }
        if page_heading_id not in owners:
            continue
        fact_ids = [str(value) for value in node.get("normalized_fact_ids") or [] if str(value) in page_fact_ids]
        statement = _text(node.get("statement"))
        if not fact_ids or not statement:
            continue
        heading_titles = {
            _title_without_number(by_id.get(page_heading_id, {}).get("title")),
            _title_without_number(statement),
        }
        if len(heading_titles) == 1:
            continue
        result.append({
            "role": role_map.get(_text(node.get("role")).lower(), "support"),
            "statement": statement,
            "evidence": {"normalized_fact_ids": fact_ids},
        })
    return result or _chain(page_facts)


def _section_id(root_id: str, root_index: int) -> str:
    return f"S{root_index:02d}"


def _default_title(normalized: dict[str, Any], workpack: dict[str, Any]) -> str:
    source_file = _text((normalized.get("source") or {}).get("source_file"))
    return Path(source_file).stem or "正式方案"


def _apply_page_spec(page: dict[str, Any], spec: dict[str, Any], heading_id: str) -> None:
    spec = _authoring_page_fields(spec)
    for field in spec:
        if field in SOURCE_BOUND_FIELDS:
            raise ValueError(f"authoring spec may not override source-bound field: {field}")
        if field not in CONTENT_FIELDS:
            raise ValueError(f"unknown authoring page field: {field}")
    page.update(deepcopy(spec))
    page["primary_source_heading_id"] = heading_id


def _require_nonempty(value: Any, field: str, heading_id: str) -> None:
    if isinstance(value, str) and value.strip():
        return
    if isinstance(value, (list, dict)) and value:
        return
    raise ValueError(f"authoring spec is incomplete for {heading_id}: {field}")


def _validate_authoring_spec_completeness(
    authoring_spec: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    content_ids: list[str],
    merge_by_heading: dict[str, dict[str, Any]],
) -> None:
    deck = authoring_spec.get("deck")
    if not isinstance(deck, dict):
        raise ValueError("authoring spec deck must be an object")
    for field in ("audience", "purpose"):
        _require_nonempty(deck.get(field), f"deck.{field}", "deck")
    pages = authoring_spec.get("pages")
    if not isinstance(pages, dict):
        raise ValueError("authoring spec pages must be an object keyed by source heading ID")
    for heading_id in content_ids:
        group = merge_by_heading.get(heading_id)
        primary = _text(group.get("primary_source_heading_id")) if isinstance(group, dict) else heading_id
        if primary != heading_id:
            continue
        spec = pages.get(heading_id)
        if not isinstance(spec, dict):
            raise ValueError(f"authoring spec is missing source heading: {heading_id}")
        fields = _authoring_page_fields(spec)
        for field in (
            "audience_question",
            "page_mission",
            "key_judgment",
            "non_substitutable_value",
            "judgment_basis",
            "argument_role",
            "must_not_include",
            "split_risk",
            "transition_from_previous",
            "transition_to_next",
            "authoring_decisions",
        ):
            _require_nonempty(fields.get(field), field, heading_id)
        for field in ("reserved_for_later", "excluded_from_onscreen"):
            if not isinstance(fields.get(field), list):
                raise ValueError(f"authoring spec is incomplete for {heading_id}: {field}")
        decisions = fields.get("authoring_decisions")
        if not isinstance(decisions, dict):
            raise ValueError(f"authoring spec is incomplete for {heading_id}: authoring_decisions")
        for field in ("deletion_test", "evidence_selection"):
            _require_nonempty(decisions.get(field), f"authoring_decisions.{field}", heading_id)
        if _is_attachment_title(by_id[heading_id].get("title")):
            disposition = _text(decisions.get("attachment_disposition"))
            if disposition not in {"main_deck", "appendix", "trace_only"}:
                raise ValueError(f"authoring spec is incomplete for {heading_id}: attachment_disposition")
            if disposition == "main_deck":
                _require_nonempty(decisions.get("attachment_promotion_rationale"), "attachment_promotion_rationale", heading_id)


def _page_source_heading_ids(
    heading_id: str,
    by_id: dict[str, dict[str, Any]],
    parents: dict[str, str | None],
) -> list[str]:
    descendants = _descendants(heading_id, parents)
    current = parents.get(heading_id)
    while current:
        descendants.add(current)
        current = parents.get(current)
    return [
        str(item["section_id"])
        for item in sorted(
            (by_id[value] for value in descendants if value in by_id),
            key=lambda item: int(item.get("order") or 0),
        )
    ]


def _build_outline(
    normalized: dict[str, Any],
    argument: dict[str, Any],
    workpack: dict[str, Any],
    authoring_spec: dict[str, Any] | None,
    concepts: dict[str, Any] | None = None,
    relations: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_id, parents = _heading_maps(workpack)
    headings = list(by_id.values())
    roots = [item for item in headings if int(item.get("level") or 0) == 1]
    content_ids = _selected_content_heading_ids(headings, authoring_spec)
    content_set = set(content_ids)
    if not content_ids:
        raise ValueError("source structure has no content headings")
    if authoring_spec is not None:
        spec_pages = authoring_spec.get("pages")
        if not isinstance(spec_pages, dict):
            raise ValueError("authoring spec pages must be an object keyed by source_heading_id")
        declared_headings = {
            str(item.get("section_id"))
            for item in headings
            if isinstance(item, dict) and item.get("section_id")
        }
        unknown = sorted(set(spec_pages) - declared_headings)
        if unknown:
            raise ValueError(f"unknown source heading in authoring spec: {unknown[0]}")
    facts = [item for item in normalized.get("facts") or [] if isinstance(item, dict) and item.get("normalized_fact_id")]
    facts_by_id = {str(item["normalized_fact_id"]): item for item in facts}
    concepts = concepts or {}
    relations = relations or {}
    argument_registry = _argument_node_registry(argument, headings, content_ids)
    planning = _spec_planning(authoring_spec)
    merge_groups = planning.get("merge_groups") if isinstance(planning.get("merge_groups"), list) else []
    merge_by_heading: dict[str, dict[str, Any]] = {}
    for group in merge_groups:
        if not isinstance(group, dict):
            raise ValueError("planning.merge_groups entries must be objects")
        primary = _text(group.get("primary_source_heading_id"))
        members = [str(value) for value in group.get("source_heading_ids") or [] if str(value)]
        if not primary or primary not in content_set or primary not in members:
            raise ValueError("merge group primary_source_heading_id must be a selected content heading")
        if not _text(group.get("rationale")):
            raise ValueError(f"merge group {primary} requires rationale")
        for member in members:
            if member not in content_set:
                raise ValueError(f"merge group references unknown content heading: {member}")
            if member in merge_by_heading and merge_by_heading[member] is not group:
                raise ValueError(f"content heading appears in more than one merge group: {member}")
            merge_by_heading[member] = group
    if authoring_spec is not None:
        _validate_authoring_spec_completeness(
            authoring_spec,
            by_id,
            content_ids,
            merge_by_heading,
        )
    root_for_content: dict[str, str] = {}
    for content_id in content_ids:
        current = content_id
        while parents.get(current):
            parent = str(parents[current])
            if int(by_id.get(parent, {}).get("level") or 0) == 1:
                root_for_content[content_id] = parent
                break
            current = parent
        root_for_content.setdefault(content_id, content_id)
    first_content = content_ids[0]
    pages: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    page_number = 1

    def add(page: dict[str, Any]) -> str:
        nonlocal page_number
        page["page_id"] = f"P{page_number:02d}"
        page["order"] = page_number
        pages.append(page)
        page_number += 1
        return str(page["page_id"])

    add({"page_type": "template", "template_role": "cover", "title_intent": _default_title(normalized, workpack)})
    add({"page_type": "template", "template_role": "agenda", "title_intent": (workpack.get("source_metadata") or {}).get("agenda_title") or "目录"})
    page_by_heading: dict[str, str] = {}
    section_page_ids: dict[str, list[str]] = {}
    section_order = 0
    for root in roots:
        root_id = str(root["section_id"])
        owned_content = [content_id for content_id in content_ids if root_for_content.get(content_id) == root_id]
        if not owned_content:
            continue
        section_order += 1
        section_id = _section_id(root_id, section_order)
        section_pages: list[str] = []
        section_pages.append(add({
            "page_type": "template",
            "template_role": "section_divider",
            "section_id": section_id,
            "title_intent": _text(root.get("title")),
            "source_heading_ids": [root_id],
            "primary_source_heading_id": root_id,
        }))
        consumed_headings: set[str] = set()
        for heading_id in owned_content:
            if heading_id in consumed_headings:
                continue
            group = merge_by_heading.get(heading_id)
            group_headings = [
                str(value)
                for value in (group.get("source_heading_ids") if isinstance(group, dict) else [heading_id])
                if str(value) in owned_content
            ]
            if heading_id not in group_headings:
                group_headings.insert(0, heading_id)
            primary_heading_id = _text(group.get("primary_source_heading_id")) if isinstance(group, dict) else heading_id
            if primary_heading_id != heading_id:
                continue
            consumed_headings.update(group_headings)
            page_facts: list[dict[str, Any]] = []
            for member_heading_id in group_headings:
                for fact in _page_facts(facts, member_heading_id, by_id, parents, content_set, first_content):
                    if fact not in page_facts:
                        page_facts.append(fact)
            if not page_facts:
                continue
            fact_ids = _fact_ids(page_facts)
            source_heading_ids = []
            for member_heading_id in group_headings:
                for source_heading_id in _page_source_heading_ids(member_heading_id, by_id, parents):
                    if source_heading_id not in source_heading_ids:
                        source_heading_ids.append(source_heading_id)
            argument_node_ids = _page_argument_nodes(
                argument_registry,
                group_headings,
                set(fact_ids),
                primary_heading_id,
            )
            concept_ids, relation_ids, inference_note = _page_graph_evidence(page_facts, concepts, relations)
            # A candidate page inventories source facts but must not fabricate a business
            # judgment: page_facts[0] may be front matter (title/date/org/TOC) with no
            # preceding heading, attributed here only via the first-content-page fallback.
            # Prefer a fact that actually sits under a heading for the human-facing preview.
            summary_facts = [fact for fact in page_facts if _nearest_heading_ids(fact, headings)] or page_facts
            candidate_summary = _text(summary_facts[0].get("statement")) or f"本节保留源材料关于{_text(by_id[heading_id].get('title'))}的内容。"
            judgment = ""
            judgment_status = "authoring_required"
            derivation = _derivation(page_facts, judgment)
            chain = _source_argument_chain(
                primary_heading_id,
                page_facts,
                argument,
                by_id,
                parents,
                content_set,
            )
            roles = _roles(page_facts, derivation)
            for evidence_id in relation_ids:
                if evidence_id not in roles["reason"]:
                    roles["reason"].append(evidence_id)
            for evidence_id in argument_node_ids:
                if evidence_id not in roles["reason"]:
                    roles["reason"].append(evidence_id)
            attachment = _is_attachment_title(by_id[primary_heading_id].get("title"))
            page = {
                "page_type": "content",
                "section_id": section_id,
                "title_intent": _text(by_id[primary_heading_id].get("title")),
                "source_heading_ids": source_heading_ids,
                "primary_source_heading_id": primary_heading_id,
                "audience_question": f"源材料如何说明{_title_without_number(by_id[primary_heading_id].get('title'))}？",
                "page_mission": f"按源材料说明{_title_without_number(by_id[primary_heading_id].get('title'))}。",
                "key_judgment": judgment,
                "judgment_status": judgment_status,
                "candidate_summary": candidate_summary,
                "judgment_derivation": derivation,
                "core_message_derivation": {
                    **derivation,
                    "argument_node_ids": argument_node_ids,
                },
                "non_substitutable_value": f"保留源材料{_title_without_number(by_id[primary_heading_id].get('title'))}的独立内容边界。",
                "judgment_basis": "source_explicit" if len(page_facts) == 1 else "source_synthesis",
                "argument_role": "background" if section_order == 1 else "support",
                "must_not_include": ["后续章节的独立页面使命"],
                "reserved_for_later": [],
                "split_risk": "low",
                "transition_from_previous": "承接源材料前页。",
                "transition_to_next": "交给源材料下一页继续展开。",
                "evidence": {
                    "normalized_fact_ids": fact_ids,
                    "relation_ids": relation_ids,
                    "argument_node_ids": argument_node_ids,
                    "concept_ids": concept_ids,
                    **({"inference_note": inference_note} if inference_note else {}),
                },
                "argument_chain": chain,
                "evidence_roles": roles,
                "excluded_from_onscreen": [],
                "content_strategy": "source_fact_inventory",
                "suggested_visual_logic": "按源材料事实组织抽象载体，不预设版式。",
                "importance": "supporting",
                "topic_category": _title_without_number(by_id[primary_heading_id].get("title")),
                "source_argument_node_ids": argument_node_ids[:1],
                "primary_argument_node_id": argument_node_ids[0],
                "source_evidence_node_ids": argument_node_ids[1:],
                "source_argument_node_roles": {
                    node_id: str(argument_registry.get(node_id, {}).get("argument_role") or "other")
                    for node_id in argument_node_ids
                },
                "source_argument_node_weights": {
                    node_id: str(argument_registry.get(node_id, {}).get("argument_weight") or "detail")
                    for node_id in argument_node_ids
                },
                "source_argument_node_statuses": {
                    node_id: str(argument_registry.get(node_id, {}).get("status") or "mixed")
                    for node_id in argument_node_ids
                },
                "semantic_projection_note": "页面级语义节点绑定来自层三论点链；缺少源节点时使用可回查的章节投影 ID，不新增源事实。",
            }
            if attachment:
                page["attachment_disposition"] = _attachment_disposition(authoring_spec, primary_heading_id)
                page["presentation_layer"] = page["attachment_disposition"]
            if isinstance(group, dict):
                page["merge_group"] = {
                    "source_heading_ids": group_headings,
                    "rationale": _text(group.get("rationale")),
                }
            if authoring_spec:
                spec_pages = authoring_spec.get("pages")
                if heading_id not in spec_pages:
                    if primary_heading_id not in spec_pages:
                        raise ValueError(f"authoring spec is missing source heading: {primary_heading_id}")
                _apply_page_spec(page, spec_pages[primary_heading_id], primary_heading_id)
                page["judgment_status"] = "author_edited"
                page.pop("candidate_summary", None)
                page["judgment_derivation"] = _derivation(page_facts, _text(page.get("key_judgment")))
                page["core_message_derivation"] = {
                    **page["judgment_derivation"],
                    "argument_node_ids": argument_node_ids,
                }
            page_id = add(page)
            for member_heading_id in group_headings:
                page_by_heading[member_heading_id] = page_id
            section_pages.append(page_id)
        section_page_ids[section_id] = section_pages
        sections.append({
            "section_id": section_id,
            "order": section_order,
            "title_intent": _text(root.get("title")),
            "section_mission": f"按源材料顺序说明{_text(root.get('title'))}的业务内容。",
            "section_thesis": f"{_text(root.get('title'))}构成全篇方案的一个源材料业务段落。",
            "argument_roles": ["source_locked"],
            "page_ids": section_pages,
        })
    add({"page_type": "template", "template_role": "closing", "title_intent": "谢谢"})

    if authoring_spec:
        spec_pages = authoring_spec.get("pages")
        unknown = []
        if isinstance(spec_pages, dict):
            for heading_id in sorted(set(spec_pages) - set(page_by_heading)):
                if _is_attachment_title(by_id.get(heading_id, {}).get("title")) and _attachment_disposition(authoring_spec, heading_id) == "trace_only":
                    continue
                unknown.append(heading_id)
        if unknown:
            raise ValueError(f"unknown source heading in authoring spec: {unknown[0]}")

    status = "author_edited" if authoring_spec else "mechanical_draft"
    spec_deck = authoring_spec.get("deck") if isinstance(authoring_spec, dict) else {}
    spec_deck = spec_deck if isinstance(spec_deck, dict) else {}
    request = workpack.get("request") or {}
    request_text = _text(request.get("text"))
    title = _text(spec_deck.get("working_title")) or _default_title(normalized, workpack)
    narrative = _text(spec_deck.get("deck_thesis")) or "按源材料章节、标题和顺序说明其业务内容。"
    deck_id = _text(spec_deck.get("deck_id")) or f"deck-{re.sub(r'[^a-zA-Z0-9]+', '-', title).strip('-').lower() or 'outline'}"
    binding = workpack.get("binding") or {}
    page_by_heading_ids = set(page_by_heading)
    fact_dispositions = [
        {
            "normalized_fact_id": str(fact["normalized_fact_id"]),
            "disposition": "intentional_omission",
            "rationale": "文档元数据或追溯信息保留在源材料层，不进入业务内容页。",
        }
        for fact in facts
        if _text(fact.get("fact_type")).lower() in NON_CONTENT_FACT_TYPES
    ]
    for fact in facts:
        fact_id = _text(fact.get("normalized_fact_id"))
        if not fact_id or fact_id in {item["normalized_fact_id"] for item in fact_dispositions}:
            continue
        heading_ids = _nearest_heading_ids(fact, headings)
        omitted_attachment = any(
            heading_id not in page_by_heading_ids
            and _is_attachment_title(by_id.get(heading_id, {}).get("title"))
            for heading_id in heading_ids
        )
        if omitted_attachment:
            fact_dispositions.append(
                {
                    "normalized_fact_id": fact_id,
                    "disposition": "intentional_omission",
                    "rationale": "附件内容默认保留在追溯层，待作者明确决定是否进入主稿或附录。",
                }
            )

    argument_dispositions: list[dict[str, Any]] = []
    for heading_id in _content_heading_ids(headings):
        heading_title = _text(by_id.get(heading_id, {}).get("title"))
        node_ids = _page_argument_nodes(
            argument_registry,
            [heading_id],
            set(_fact_ids(_page_facts(facts, heading_id, by_id, parents, content_set, first_content))),
            heading_id,
        )
        node_id = node_ids[0]
        page_id = page_by_heading.get(heading_id)
        if page_id:
            group = merge_by_heading.get(heading_id)
            primary = _text(group.get("primary_source_heading_id")) if isinstance(group, dict) else heading_id
            if primary == heading_id:
                argument_dispositions.append({
                    "node_id": node_id,
                    "disposition": "standalone_page",
                    "page_id": page_id,
                    "rationale": "候选生成按源章节建立页面承载，作者可在 authoring-spec 中明确合并或拆分。",
                })
            else:
                argument_dispositions.append({
                    "node_id": node_id,
                    "disposition": "merged_page",
                    "page_id": page_id,
                    "rationale": _text((group or {}).get("rationale")) or "按作者明确的合并组承载。",
                    "merge_reason": _text((group or {}).get("rationale")) or "作者明确指定同一页面主题。",
                    "shared_page_topic": _title_without_number(by_id.get(primary, {}).get("title")),
                })
        else:
            argument_dispositions.append({
                "node_id": node_id,
                "disposition": "intentional_omission",
                "rationale": "附件标题默认仅作追溯清单，不自动进入主内容页。",
                "omission_reason": "默认附件处置为 trace_only，等待作者决定。",
                "retained_for": ["traceability_only"],
            })

    planning_page_budget = planning.get("page_budget") if isinstance(planning.get("page_budget"), dict) else {}
    target_budget = planning_page_budget.get("target")
    min_budget = planning_page_budget.get("min")
    max_budget = planning_page_budget.get("max")
    page_budget = {
        "target": target_budget if isinstance(target_budget, int) and target_budget > 0 else len(pages),
        "min": min_budget if isinstance(min_budget, int) and min_budget > 0 else len(pages),
        "max": max_budget if isinstance(max_budget, int) and max_budget > 0 else len(pages),
    }
    root_fields = {
        "schema_version": "1.1",
        "artifact_type": "ppt_deck_brief",
        "deck_id": deck_id,
        "communication_goal": _text(spec_deck.get("communication_goal")) or request_text or "按源材料完成正式交流说明。",
        "narrative_thesis": narrative,
        "architecture_mode": "solution",
        "architecture_reason": "正式方案材料默认采用源结构锁定的方案型架构。",
        "structure_principle": "保留源材料章节、标题和顺序；作者化输入只覆盖明确编辑字段。",
        "workpack_binding": {"request_sha256": binding.get("request_sha256"), "planning_policy_sha256": binding.get("planning_policy_sha256")},
        "task_understanding": {
            "audience": _text(spec_deck.get("audience")) or "按当前交流目标确定",
            "purpose": _text(spec_deck.get("purpose")) or request_text or "按源材料完成正式交流说明。",
            "writing_style_mode": (workpack.get("planning_policy") or {}).get("writing_style_mode", "government_official"),
            "source_structure_mode": (workpack.get("planning_policy") or {}).get("source_structure_mode", "locked"),
            "assumptions": [] if authoring_spec else ["页面使命、核心判断和证据取舍尚未完成人工作者化。"],
        },
        "deck_strategy": {
            "working_title": title,
            "core_question": _text(spec_deck.get("core_question")) or "源材料说明了什么业务安排？",
            "deck_thesis": narrative,
            "page_budget": page_budget,
            "page_budget_rationale": "由源材料结构、明确合并组和作者页数约束确定；未声明时按当前候选页数记录。",
            "decision_path": [_text(section.get("title_intent")) for section in sections],
            "deck_type": "正式方案交流",
            "narrative_mode": "source_logic_focused",
        },
        "planning_policy": deepcopy(workpack.get("planning_policy") or {}),
        "title_style_mode": "formal_plain",
        "editorial_control_mode": "required",
        "editorial_authoring_mode": "author_driven",
        "editorial_authoring_status": status,
        "core_message_derivation_mode": "required",
        "argument_contract_mode": "strict",
        "semantic_argument_model_mode": "required",
        "argument_node_disposition_mode": "required",
        "argument_node_registry": list(argument_registry.values()),
        "concept_graph_summary": {
            "concept_ids": [str(item.get("concept_id")) for item in concepts.get("concepts") or [] if isinstance(item, dict) and item.get("concept_id")],
            "relation_ids": [str(item.get("relation_id")) for item in relations.get("relations") or [] if isinstance(item, dict) and item.get("relation_id")],
        },
        "attachment_policy": {
            "default_disposition": "trace_only",
            "author_decision_required_for_main_deck": True,
        },
        "sections": sections,
    }
    plan = {
        "schema_version": "1.1",
        "artifact_type": "ppt_page_plan",
        "deck_id": deck_id,
        "communication_goal": root_fields["communication_goal"],
        "narrative_thesis": narrative,
        "planning_policy": deepcopy(workpack.get("planning_policy") or {}),
        "editorial_control_mode": "required",
        "editorial_authoring_mode": "author_driven",
        "editorial_authoring_status": status,
        "core_message_derivation_mode": "required",
        "argument_contract_mode": "strict",
        "semantic_argument_model_mode": "required",
        "argument_node_disposition_mode": "required",
        "argument_node_registry": list(argument_registry.values()),
        "argument_node_dispositions": argument_dispositions,
        "fact_dispositions": fact_dispositions,
        "concept_graph": {
            "concept_ids": [str(item.get("concept_id")) for item in concepts.get("concepts") or [] if isinstance(item, dict) and item.get("concept_id")],
            "relation_ids": [str(item.get("relation_id")) for item in relations.get("relations") or [] if isinstance(item, dict) and item.get("relation_id")],
        },
        "page_budget_policy": page_budget,
        "merge_groups": deepcopy(merge_groups),
        "attachment_policy": {
            "default_disposition": "trace_only",
            "author_decision_required_for_main_deck": True,
        },
        "pages": pages,
    }
    return root_fields, plan


def generate_outline(
    semantic_dir: Path | str,
    outline_dir: Path | str,
    *,
    authoring_spec: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Generate official layer-four Outline artifacts.

    Without ``authoring_spec`` the result is an explicitly marked candidate;
    with a complete spec it is an authored Outline subject to validation.
    """
    semantic = Path(semantic_dir).expanduser().resolve()
    outline = Path(outline_dir).expanduser().resolve()
    if not semantic.is_dir():
        raise FileNotFoundError(f"semantic directory does not exist: {semantic}")
    if outline.exists() and not force and (outline / "deck-brief.json").exists():
        raise FileExistsError(f"Outline already exists: {outline}")
    normalized, argument, _report, workpack = _load_inputs(semantic, outline)
    concepts = _read(semantic / "concept-base.json")
    relations = _read(semantic / "relation-graph.json")
    deck, plan = _build_outline(
        normalized,
        argument,
        workpack,
        authoring_spec,
        concepts,
        relations,
    )
    _write(outline / "deck-brief.json", deck)
    _write(outline / "page-plan.json", plan)
    return {
        "status": "generated",
        "authoring_status": plan["editorial_authoring_status"],
        "handoff_status": "blocked" if plan["editorial_authoring_status"] != "author_edited" else "pending_validation",
        "deck": str(outline / "deck-brief.json"),
        "plan": str(outline / "page-plan.json"),
        "page_count": len(plan["pages"]),
        "content_pages": sum(page.get("page_type") == "content" for page in plan["pages"]),
    }
