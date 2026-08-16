from __future__ import annotations

from collections import defaultdict
from typing import Any

from .mappings import ARGUMENT_DUTY, IMPORTANCE_TO_WEIGHT, normalize_importance
from .source_projection import _anchors, _flatten_sections


def layer_four_page_node_id(page: dict[str, Any]) -> str:
    return f"L4-{str(page.get('page_id') or '').upper()}"

def _node_importance(arg_id: str, page_plan: dict[str, Any]) -> str:
    rank = {"low": 0, "medium": 1, "high": 2}
    current = "low"
    for page in page_plan.get("pages") or []:
        if not isinstance(page, dict) or page.get("page_type") != "content":
            continue
        ids = (page.get("evidence") or {}).get("argument_node_ids") or []
        page_importance = normalize_importance(page.get("importance"))
        if arg_id in ids and rank.get(page_importance, 0) > rank[current]:
            current = page_importance
    return current

def _primary_page_for_arg(arg_id: str, page_plan: dict[str, Any]) -> str:
    for page in page_plan.get("pages") or []:
        if isinstance(page, dict) and page.get("page_type") == "content" and arg_id in ((page.get("evidence") or {}).get("argument_node_ids") or []):
            return f"p{int(page.get('order')):02d}"
    return ""

def _project_semantic_model(payloads: dict[str, dict[str, Any]], nf_to_st: dict[str, str], block_map: dict[str, str], section_map: dict[str, str]) -> dict[str, Any]:
    argument = payloads["argument"]
    structure = payloads["structure"]
    deck = payloads["deck"]
    page_plan = payloads["page_plan"]
    normalized_by_id = {str(item.get("normalized_fact_id")): item for item in payloads["normalized"].get("facts") or [] if isinstance(item, dict)}
    source_arg_by_facts: dict[tuple[str, ...], dict[str, Any]] = {}
    for item in argument.get("source_chain") or []:
        if isinstance(item, dict):
            source_arg_by_facts[tuple(sorted(str(x) for x in item.get("normalized_fact_ids") or []))] = item
    section_titles = {str(item.get("section_id")): str(item.get("title") or "") for item in _flatten_sections(structure.get("outline") or []) if item.get("section_id")}
    section_nodes: list[dict[str, Any]] = []
    sections_with_args: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in argument.get("reconstructed_chain") or []:
        if isinstance(node, dict):
            for sec in node.get("section_ids") or []:
                sections_with_args[str(sec)].append(node)
    for sec_id, nodes in sections_with_args.items():
        source_refs = sorted({block_map.get(str(ev.get("block_id"))) for node in nodes for nf in node.get("normalized_fact_ids") or [] for ev in normalized_by_id.get(str(nf), {}).get("evidence") or [] if block_map.get(str(ev.get("block_id")))})
        role = str(nodes[0].get("role") or "other")
        section_nodes.append({
            "id": sec_id, "source_heading_id": section_map.get(sec_id), "source_heading": section_titles.get(sec_id, sec_id),
            "section_thesis": "；".join(str(node.get("statement") or "") for node in nodes),
            "argument_role": role, "argument_weight": IMPORTANCE_TO_WEIGHT.get(max((_node_importance(str(node.get('node_id')), page_plan) for node in nodes), key=lambda x: {"low":0,"medium":1,"high":2}[x], default="low"), "detail"),
            "level": 1, "status": "mixed", "evidence_refs": source_refs, "actor_refs": [],
            "primary_consumer": _primary_page_for_arg(str(nodes[0].get("node_id")), page_plan), "subsection_ids": [str(node.get("node_id")) for node in nodes],
            "allowed_merges": [], "claim_origin": "source_implied", "source_gap_ids": [], "projection_only": True,
        })
    subsection_nodes: list[dict[str, Any]] = []
    for node in argument.get("reconstructed_chain") or []:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("node_id") or "")
        facts = [str(x) for x in node.get("normalized_fact_ids") or []]
        source_units = sorted({block_map.get(str(ev.get("block_id"))) for nf in facts for ev in normalized_by_id.get(nf, {}).get("evidence") or [] if block_map.get(str(ev.get("block_id")))})
        sec_id = str((node.get("section_ids") or [""])[0])
        source_node = source_arg_by_facts.get(tuple(sorted(facts)))
        claim_origin = "source_explicit" if source_node and str(source_node.get("statement") or "") == str(node.get("statement") or "") else "source_implied"
        subsection_nodes.append({
            "id": node_id, "parent_id": sec_id, "source_heading_id": section_map.get(sec_id), "source_heading": section_titles.get(sec_id, sec_id),
            "section_thesis": str(node.get("statement") or ""), "thesis": str(node.get("statement") or ""),
            "argument_role": str(node.get("role") or "other"), "argument_weight": IMPORTANCE_TO_WEIGHT.get(_node_importance(node_id, page_plan), "detail"),
            "level": 2, "status": "mixed", "evidence_refs": source_units, "actor_refs": [], "primary_consumer": _primary_page_for_arg(node_id, page_plan),
            "subsection_ids": [], "allowed_merges": [], "claim_origin": claim_origin, "source_gap_ids": [], "projection_only": True,
        })
    for page in page_plan.get("pages") or []:
        if not isinstance(page, dict) or page.get("page_type") != "content":
            continue
        fact_ids = [
            str(value)
            for value in ((page.get("evidence") or {}).get("normalized_fact_ids") or [])
        ]
        source_units = sorted(
            {
                block_map.get(str(ev.get("block_id")))
                for nf in fact_ids
                for ev in normalized_by_id.get(nf, {}).get("evidence") or []
                if block_map.get(str(ev.get("block_id")))
            }
        )
        subsection_nodes.append(
            {
                "id": layer_four_page_node_id(page),
                "parent_id": str(page.get("section_id") or ""),
                "source_heading_id": None,
                "source_heading": str(page.get("title_intent") or ""),
                "section_thesis": str(page.get("key_judgment") or ""),
                "thesis": str(page.get("key_judgment") or ""),
                "argument_role": str(page.get("argument_role") or "source_exposition"),
                "argument_weight": IMPORTANCE_TO_WEIGHT.get(
                    normalize_importance(page.get("importance")), "detail"
                ),
                "level": 3,
                "status": (
                    "proposed"
                    if page.get("judgment_basis") == "planning_inference"
                    else "mixed"
                ),
                "evidence_refs": source_units,
                "actor_refs": [],
                "primary_consumer": f"p{int(page.get('order') or 0):02d}",
                "required_for_primary_consumer": True,
                "subsection_ids": [],
                "allowed_merges": [],
                "claim_origin": (
                    "source_implied"
                    if page.get("judgment_basis") == "planning_inference"
                    else "source_explicit"
                ),
                "source_gap_ids": [],
                "authority_ref": str(page.get("page_id") or ""),
                "projection_only": True,
            }
        )
    arg_by_fact: dict[str, list[str]] = defaultdict(list)
    for node in subsection_nodes:
        if str(node.get("id") or "").startswith("L4-"):
            page_id = str(node.get("authority_ref") or "")
            page = next(
                (
                    item
                    for item in page_plan.get("pages") or []
                    if isinstance(item, dict) and str(item.get("page_id") or "") == page_id
                ),
                {},
            )
            for nf in ((page.get("evidence") or {}).get("normalized_fact_ids") or []):
                arg_by_fact[str(nf)].append(str(node["id"]))
            continue
        original = next((item for item in argument.get("reconstructed_chain") or [] if isinstance(item, dict) and str(item.get("node_id")) == node["id"]), {})
        for nf in original.get("normalized_fact_ids") or []:
            arg_by_fact[str(nf)].append(str(node["id"]))
    relations: list[dict[str, Any]] = []
    inference_register: list[dict[str, Any]] = []
    concept_by_id = {str(item.get("concept_id")): item for item in payloads["concepts"].get("concepts") or [] if isinstance(item, dict)}
    for rel in payloads["relations"].get("relations") or []:
        if not isinstance(rel, dict):
            continue
        rel_id = str(rel.get("relation_id") or "")
        rel_facts = [str(x) for x in rel.get("normalized_fact_ids") or []]
        candidate_nodes = [node for fact in rel_facts for node in arg_by_fact.get(fact, [])]
        from_concept = concept_by_id.get(str(rel.get("from_concept_id")), {})
        to_concept = concept_by_id.get(str(rel.get("to_concept_id")), {})
        from_nodes = [node for fact in from_concept.get("normalized_fact_ids") or [] for node in arg_by_fact.get(str(fact), [])]
        to_nodes = [node for fact in to_concept.get("normalized_fact_ids") or [] for node in arg_by_fact.get(str(fact), [])]
        from_node = (from_nodes or candidate_nodes or [""])[0]
        to_node = (to_nodes or candidate_nodes or [from_node])[0]
        basis = str(rel.get("basis") or "explicit")
        item = {
            "id": rel_id, "authority_ref": rel_id, "from_node_id": from_node, "to_node_id": to_node,
            "relation_type": str(rel.get("relation_type") or "relates_to"), "weight_effect": "none",
            "basis": basis, "claim_origin": "source_explicit" if basis == "explicit" else "source_implied",
            "evidence_refs": sorted({block_map.get(str(ev.get("block_id"))) for nf in rel_facts for ev in normalized_by_id.get(nf, {}).get("evidence") or [] if block_map.get(str(ev.get("block_id")))}),
            "confidence": rel.get("confidence"), "projection_only": True,
        }
        if basis == "inferred":
            item["inference_rationale"] = str(rel.get("inference_rationale") or "")
            inference_register.append({"inference_id": f"INF-{rel_id}", "claim_origin": "source_implied", "basis": item["inference_rationale"], "affected_nodes": [from_node, to_node], "authority_ref": rel_id, "handling": "Preserve as inferred; never upgrade to source_explicit."})
        relations.append(item)
    coverage_assignments: list[dict[str, Any]] = []
    for nf_id, fact in normalized_by_id.items():
        node_ids = arg_by_fact.get(nf_id, [])
        source_units = [block_map.get(str(ev.get("block_id"))) for ev in fact.get("evidence") or []]
        source_units = [item for item in source_units if item]
        heading_path = []
        if fact.get("evidence"):
            first_block = str((fact.get("evidence") or [{}])[0].get("block_id") or "")
            block = next((item for item in structure.get("blocks") or [] if isinstance(item, dict) and str(item.get("block_id")) == first_block), {})
            heading_path = list(block.get("heading_path") or [])
        duty = ARGUMENT_DUTY.get(str(next((item.get("role") for item in argument.get("reconstructed_chain") or [] if isinstance(item, dict) and str(item.get("node_id")) in node_ids), "other")), "detail")
        coverage_assignments.append({
            "source_unit_refs": source_units, "semantic_node_ids": node_ids,
            "atomic_items": [{"item_id": nf_id, "statement": str(fact.get("statement") or ""), "source_unit_refs": source_units, "status": "unknown", "argument_duty": duty, "coverage_anchors": _anchors(str(fact.get("statement") or ""), heading_path), "authority_ref": nf_id}],
            "authority_ref": nf_id, "projection_only": True,
        })
    strategy = deck.get("deck_strategy") or {}
    task = deck.get("task_understanding") or {}
    concepts = payloads["concepts"].get("concepts") or []
    model = {
        "schema": "cyberppt.semantic_argument_model.v1", "version": 1, "interpretation_contract_mode": "projection",
        "authority_mode": "projection_only",
        "document_semantics": {
            "document_role": str(strategy.get("deck_type") or "presentation"),
            "subject_of_report": str(strategy.get("working_title") or structure.get("document", {}).get("title") or ""),
            "primary_thesis": str(strategy.get("deck_thesis") or ""),
            "decision_boundary": "Compatibility projection only; epistemic strength is inherited from layer-three and layer-four artifacts.",
            "author_purpose": str(task.get("purpose") or ""),
            "argument_method": [str(item.get("statement") or "") for item in argument.get("reconstructed_chain") or [] if isinstance(item, dict)],
            "supporting_basis": [str(item.get("statement") or "") for item in payloads["normalized"].get("facts") or [] if isinstance(item, dict)],
            "business_objects": [str(item.get("canonical_name") or "") for item in concepts if isinstance(item, dict)],
            "scope": "", "decision_intent": str(task.get("purpose") or ""),
        },
        "document_thesis": {"statement": str(strategy.get("deck_thesis") or ""), "argument_role": "thesis", "argument_weight": "core", "status": "mixed", "evidence_refs": sorted({ref for item in subsection_nodes for ref in item.get("evidence_refs") or []}), "actor_refs": [], "claim_origin": "source_implied", "projection_only": True},
        "section_nodes": section_nodes, "subsection_nodes": subsection_nodes, "argument_relations": relations,
        "mece_rules": {"partition_basis": "Validated layer-four deck sections", "exhaustive_scope": "Validated layer-four page plan", "overlap_policy": "Use must_not_include/reserved_for_later page boundaries", "groups": [], "review_notes": ["Projection only; no MECE inference was performed in this adapter."]},
        "inference_register": inference_register,
        "concept_occurrence_graph": {"concepts": concepts, "relations": payloads["relations"].get("relations") or [], "review_notes": ["Copied from authoritative layer-three concept/relation artifacts."]},
        "source_coverage": {"assignments": coverage_assignments, "intentional_omissions": [], "review_notes": ["Coverage is projected from normalized-fact evidence; no new semantic assignment is invented."]},
        "semantic_content_unit_coverage_mode": "projection", "source_gaps": payloads["argument"].get("diagnostics") or [],
    }
    return model
