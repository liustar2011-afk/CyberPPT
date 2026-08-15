"""Prepare the bounded human authoring input for layer-four Outline planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .generate import (
    _content_heading_ids,
    _fact_ids,
    _heading_maps,
    _load_inputs,
    _page_facts,
)


AUTHORING_FIELDS = (
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
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _fact_ids_for_heading(
    facts: list[dict[str, Any]],
    heading_id: str,
    by_id: dict[str, dict[str, Any]],
    parents: dict[str, str | None],
    content_ids: set[str],
    fallback_heading_id: str,
) -> list[str]:
    return _fact_ids(_page_facts(facts, heading_id, by_id, parents, content_ids, fallback_heading_id))


def _argument_nodes_for_heading(
    argument: dict[str, Any],
    heading_id: str,
    fact_ids: set[str],
) -> list[str]:
    result: list[str] = []
    for group_name in ("source_chain", "reconstructed_chain"):
        for node in argument.get(group_name) or []:
            if not isinstance(node, dict) or not node.get("node_id"):
                continue
            section_ids = {str(value) for value in node.get("section_ids") or []}
            node_facts = {str(value) for value in node.get("normalized_fact_ids") or []}
            if heading_id in section_ids and node_facts.intersection(fact_ids):
                node_id = str(node["node_id"])
                if node_id not in result:
                    result.append(node_id)
    return result


def _relation_ids_for_facts(
    relations: dict[str, Any],
    fact_ids: set[str],
) -> list[str]:
    result: list[str] = []
    for relation in relations.get("relations") or []:
        if not isinstance(relation, dict) or not relation.get("relation_id"):
            continue
        refs = {str(value) for value in relation.get("normalized_fact_ids") or []}
        if refs and refs.issubset(fact_ids):
            result.append(str(relation["relation_id"]))
    return result


def _concept_ids_for_facts(concepts: dict[str, Any], fact_ids: set[str]) -> list[str]:
    result: list[str] = []
    for concept in concepts.get("concepts") or []:
        if not isinstance(concept, dict) or not concept.get("concept_id"):
            continue
        refs = {str(value) for value in concept.get("normalized_fact_ids") or []}
        if refs.intersection(fact_ids):
            result.append(str(concept["concept_id"]))
    return result


def prepare_authoring_spec(
    semantic_dir: Path | str,
    outline_dir: Path | str,
    output_path: Path | str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Write a source-bound, blank authoring template.

    The template exposes source context and leaves editorial fields blank. It
    is intentionally not an Outline and cannot be used to bypass the author
    gate without page-level decisions.
    """

    output = Path(output_path).expanduser().resolve()
    if output.exists() and not force:
        raise FileExistsError(f"authoring spec already exists: {output}")
    normalized, argument, _report, workpack = _load_inputs(
        Path(semantic_dir).expanduser().resolve(),
        Path(outline_dir).expanduser().resolve(),
    )
    concepts = _read(Path(semantic_dir).expanduser().resolve() / "concept-base.json")
    relations = _read(Path(semantic_dir).expanduser().resolve() / "relation-graph.json")
    by_id, parents = _heading_maps(workpack)
    headings = list(by_id.values())
    content_ids = _content_heading_ids(headings)
    content_id_set = set(content_ids)
    fallback_heading_id = content_ids[0]
    facts = [
        item
        for item in normalized.get("facts") or []
        if isinstance(item, dict) and item.get("normalized_fact_id")
    ]
    pages: dict[str, Any] = {}
    for heading_id in content_ids:
        heading = by_id[heading_id]
        fact_ids = _fact_ids_for_heading(facts, heading_id, by_id, parents, content_id_set, fallback_heading_id)
        fact_set = set(fact_ids)
        pages[heading_id] = {
            "source_heading_id": heading_id,
            "source_title": _text(heading.get("title")),
            "source_fact_ids": fact_ids,
            "source_argument_node_ids": _argument_nodes_for_heading(argument, heading_id, fact_set),
            "source_concept_ids": _concept_ids_for_facts(concepts, fact_set),
            "source_relation_ids": _relation_ids_for_facts(relations, fact_set),
            "authoring": {field: "" for field in AUTHORING_FIELDS},
        }
        pages[heading_id]["authoring"]["must_not_include"] = []
        pages[heading_id]["authoring"]["reserved_for_later"] = []
        pages[heading_id]["authoring"]["excluded_from_onscreen"] = []
        pages[heading_id]["authoring"]["evidence_roles"] = {}
        pages[heading_id]["authoring"]["argument_chain"] = []
        pages[heading_id]["authoring"]["authoring_decisions"] = {}

    spec = {
        "schema_version": "1.0",
        "artifact_type": "ppt_outline_authoring_spec",
        "authority": "layer-three-semantic-foundation",
        "workpack_binding": dict(workpack.get("binding") or {}),
        "deck": {
            "audience": "",
            "purpose": "",
            "working_title": "",
            "core_question": "",
            "deck_thesis": "",
            "communication_goal": "",
        },
        "planning": {
            "page_budget": {"target": "", "min": "", "max": ""},
            "merge_groups": [],
            "default_attachment_disposition": "trace_only",
        },
        "pages": pages,
    }
    _write(output, spec)
    return {
        "status": "prepared",
        "output": str(output),
        "page_count": len(pages),
        "content_headings": list(pages),
    }


__all__ = ["prepare_authoring_spec"]
